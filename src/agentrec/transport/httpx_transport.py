"""Sync and async httpx transports for session record/replay."""

from __future__ import annotations

import base64
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from agentrec.cassette.model import ErrorRecord, Interaction
from agentrec.errors import ReplayedTransportError, ReplayMissError
from agentrec.session import Session

from ._legacy_sse import AsyncRecordingStream, RecordingStream

LOGGER = logging.getLogger("agentrec")


def _warn_large(session: Session, label: str, body: bytes) -> None:
    if len(body) > session.max_body_bytes:
        LOGGER.warning(
            "%s body size %d exceeds configured %d bytes",
            label,
            len(body),
            session.max_body_bytes,
        )


def _stored_body(content: bytes) -> dict[str, str]:
    try:
        return {"body": content.decode("utf-8"), "body_encoding": "text"}
    except UnicodeDecodeError:
        return {
            "body": base64.b64encode(content).decode("ascii"),
            "body_encoding": "base64",
        }


def _body_bytes(record: dict[str, Any]) -> bytes:
    body = record.get("body", "")
    if record.get("body_encoding") == "base64":
        return base64.b64decode(body, validate=True)
    return str(body).encode("utf-8")


def _headers(headers: httpx.Headers) -> dict[str, str]:
    return {name.lower(): value for name, value in headers.items()}


def _response_headers(response: httpx.Response) -> dict[str, str]:
    return {
        name: value
        for name, value in _headers(response.headers).items()
        if name not in {"content-encoding", "content-length"}
    }


def _request_record(request: httpx.Request, content: bytes) -> dict[str, Any]:
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": _headers(request.headers),
        **_stored_body(content),
    }


def _record_response(
    response: httpx.Response, body: bytes, *, streamed: bool
) -> dict[str, Any]:
    return {
        "status": response.status_code,
        "headers": _response_headers(response),
        **_stored_body(body),
        "streamed": streamed,
    }


def _replay_response(item: Interaction, request: httpx.Request) -> httpx.Response:
    if item.error:
        error_type = getattr(httpx, item.error.type, None)
        if isinstance(error_type, type) and issubclass(error_type, httpx.RequestError):
            raise error_type(item.error.message, request=request)
        raise ReplayedTransportError(f"{item.error.type}: {item.error.message}")
    if item.response is None:
        raise ReplayMissError(f"recorded HTTP interaction {item.seq} has no response")
    response = item.response
    content = _body_bytes(response)
    if response.get("streamed"):
        return httpx.Response(
            response["status"],
            headers=response["headers"],
            stream=httpx.ByteStream(content),
            request=request,
        )
    return httpx.Response(
        response["status"],
        headers=response["headers"],
        content=content,
        request=request,
    )


class RecordReplayTransport(httpx.BaseTransport):
    """Intercept sync HTTP boundaries without changing the SDK client code."""

    def __init__(
        self, session: Session, inner: httpx.BaseTransport | None = None
    ) -> None:
        """Bind a session and optional fake or live upstream transport."""
        self.session = session
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Replay a matching occurrence or record the upstream outcome."""
        content = request.read()
        _warn_large(self.session, "request", content)
        headers = _headers(request.headers)
        key = self.session.match_policy.http_key(
            request.method, str(request.url), content, headers
        )
        record = _request_record(request, content)
        played = self.session._lookup(key, record)
        if played is not None:
            return _replay_response(played, request)
        if not self.session._recording_allowed():
            raise ReplayMissError(f"HTTP replay miss: {request.method} {request.url}")
        inner = self.inner or httpx.HTTPTransport()
        forwarded = httpx.Request(
            request.method,
            request.url,
            headers=request.headers,
            content=content,
            extensions=request.extensions,
        )
        started = datetime.now(UTC)
        tick = time.perf_counter()
        try:
            response = inner.handle_request(forwarded)
        except httpx.RequestError as exc:
            self.session._append(
                "http",
                key,
                record,
                None,
                ErrorRecord(type=type(exc).__name__, message=str(exc)),
                started,
                (time.perf_counter() - tick) * 1000,
            )
            raise
        streamed = (
            "text/event-stream" in response.headers.get("content-type", "").lower()
        )
        if streamed:

            def complete(body: bytes) -> None:
                _warn_large(self.session, "response", body)
                self.session._append(
                    "http",
                    key,
                    record,
                    _record_response(response, body, streamed=True),
                    None,
                    started,
                    (time.perf_counter() - tick) * 1000,
                )

            return httpx.Response(
                response.status_code,
                headers=_response_headers(response),
                stream=RecordingStream(response, complete),
                request=request,
            )
        body = response.read()
        _warn_large(self.session, "response", body)
        self.session._append(
            "http",
            key,
            record,
            _record_response(response, body, streamed=False),
            None,
            started,
            (time.perf_counter() - tick) * 1000,
        )
        return httpx.Response(
            response.status_code,
            headers=_response_headers(response),
            content=body,
            request=request,
        )

    def close(self) -> None:
        """Close an explicitly supplied upstream transport."""
        if self.inner is not None:
            self.inner.close()


class AsyncRecordReplayTransport(httpx.AsyncBaseTransport):
    """Intercept async HTTP boundaries without changing the SDK client code."""

    def __init__(
        self, session: Session, inner: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """Bind a session and optional fake or live async upstream transport."""
        self.session = session
        self.inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Replay a matching occurrence or record the async upstream outcome."""
        content = await request.aread()
        _warn_large(self.session, "request", content)
        headers = _headers(request.headers)
        key = self.session.match_policy.http_key(
            request.method, str(request.url), content, headers
        )
        record = _request_record(request, content)
        played = self.session._lookup(key, record)
        if played is not None:
            return _replay_response(played, request)
        if not self.session._recording_allowed():
            raise ReplayMissError(f"HTTP replay miss: {request.method} {request.url}")
        inner = self.inner or httpx.AsyncHTTPTransport()
        forwarded = httpx.Request(
            request.method,
            request.url,
            headers=request.headers,
            content=content,
            extensions=request.extensions,
        )
        started = datetime.now(UTC)
        tick = time.perf_counter()
        try:
            response = await inner.handle_async_request(forwarded)
        except httpx.RequestError as exc:
            self.session._append(
                "http",
                key,
                record,
                None,
                ErrorRecord(type=type(exc).__name__, message=str(exc)),
                started,
                (time.perf_counter() - tick) * 1000,
            )
            raise
        streamed = (
            "text/event-stream" in response.headers.get("content-type", "").lower()
        )
        if streamed:

            def complete(body: bytes) -> None:
                _warn_large(self.session, "response", body)
                self.session._append(
                    "http",
                    key,
                    record,
                    _record_response(response, body, streamed=True),
                    None,
                    started,
                    (time.perf_counter() - tick) * 1000,
                )

            return httpx.Response(
                response.status_code,
                headers=_response_headers(response),
                stream=AsyncRecordingStream(response, complete),
                request=request,
            )
        body = await response.aread()
        _warn_large(self.session, "response", body)
        self.session._append(
            "http",
            key,
            record,
            _record_response(response, body, streamed=False),
            None,
            started,
            (time.perf_counter() - tick) * 1000,
        )
        return httpx.Response(
            response.status_code,
            headers=_response_headers(response),
            content=body,
            request=request,
        )

    async def aclose(self) -> None:
        """Close an explicitly supplied async upstream transport."""
        if self.inner is not None:
            await self.inner.aclose()
