"""Traffic-edge regressions for SDK retries, encoding, binary, and streams."""

from __future__ import annotations

import asyncio
import gzip
import json
from collections.abc import Iterator
from pathlib import Path

import anthropic
import httpx2
import openai
import pytest

import agentrec
from agentrec.cassette.store import CassetteStore


def _chat_response() -> dict[str, object]:
    return {
        "id": "chatcmpl-retry",
        "object": "chat.completion",
        "created": 1,
        "model": "fake-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "recovered"},
                "finish_reason": "stop",
            }
        ],
    }


def test_openai_sdk_retry_500_then_200_replays_same_occurrences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "openai-retry"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(500, json={"error": {"message": "retry"}})
        return httpx2.Response(200, json=_chat_response())

    def invoke(rec: agentrec.Session) -> str | None:
        client = openai.OpenAI(
            api_key="test",
            base_url="https://example.test/v1",
            max_retries=1,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            return (
                client.chat.completions.create(
                    model="fake-model", messages=[{"role": "user", "content": "same"}]
                )
                .choices[0]
                .message.content
            )
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == "recovered"
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == "recovered"
        assert rec.play_count == 2
    assert calls == 2
    _, interactions = CassetteStore(path).load()
    assert [item.occurrence for item in interactions] == [0, 1]
    assert [item.response["status"] for item in interactions] == [500, 200]


def test_anthropic_sdk_retry_500_then_200_replays_same_occurrences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "anthropic-retry"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(
                500,
                json={
                    "type": "error",
                    "error": {"type": "api_error", "message": "retry"},
                },
            )
        return httpx2.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-test",
                "content": [{"type": "text", "text": "recovered"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    def invoke(rec: agentrec.Session) -> str:
        client = anthropic.Anthropic(
            api_key="test",
            base_url="https://example.test",
            max_retries=1,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            result = client.messages.create(
                model="claude-test",
                max_tokens=10,
                messages=[{"role": "user", "content": "same"}],
            )
            return result.content[0].text
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == "recovered"
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == "recovered"
        assert rec.play_count == 2
    assert calls == 2


def test_gzip_body_is_decoded_and_replay_headers_are_safe(tmp_path: Path) -> None:
    path = tmp_path / "gzip"
    plain = b'{"answer":"decoded"}'
    compressed = gzip.compress(plain)
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200,
            headers={
                "content-type": "application/json",
                "content-encoding": "gzip",
                "content-length": str(len(compressed)),
            },
            content=compressed,
        )

    def invoke(rec: agentrec.Session) -> tuple[bytes, dict[str, str]]:
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            response = client.get("https://example.test/gzip")
            return response.content, dict(response.headers)

    with agentrec.session(path, mode="once") as rec:
        body, headers = invoke(rec)
        assert body == plain
        assert "content-encoding" not in headers
    with agentrec.session(path, mode="none") as rec:
        body, headers = invoke(rec)
        assert body == plain
        assert "content-encoding" not in headers
        assert headers.get("content-length") == str(len(plain))
    assert calls == 1


def test_binary_request_and_response_use_base64_without_loss(tmp_path: Path) -> None:
    path = tmp_path / "binary"
    request_bytes = b"\x00\xff\x10"
    response_bytes = b"\xff\x00\x80"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert request.content == request_bytes
        return httpx2.Response(
            200,
            headers={"content-type": "application/octet-stream"},
            content=response_bytes,
        )

    def invoke(rec: agentrec.Session) -> bytes:
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            return client.post(
                "https://example.test/upload",
                content=request_bytes,
            ).content

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == response_bytes
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == response_bytes
    assert calls == 1
    _, interactions = CassetteStore(path).load()
    assert interactions[0].request["body_encoding"] == "base64"
    assert interactions[0].response["body_encoding"] == "base64"


def test_large_body_warns_and_is_never_truncated(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "large"
    payload = b"1234567890"

    def upstream(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=payload)

    with (
        agentrec.session(path, mode="once", max_body_bytes=3) as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        assert (
            client.post("https://example.test/large", content=payload).content
            == payload
        )
    assert (
        len([record for record in caplog.records if "body size" in record.message]) == 2
    )
    _, interactions = CassetteStore(path).load()
    assert interactions[0].response["body"] == "1234567890"


class ChunkedRequest(httpx2.SyncByteStream):
    """Supply request body bytes in two pieces to the transport."""

    def __iter__(self) -> Iterator[bytes]:
        """Yield the complete request progressively."""
        yield b"first"
        yield b"second"

    def close(self) -> None:
        """Permit client cleanup."""


def test_consumed_request_stream_is_forwarded_complete(tmp_path: Path) -> None:
    path = tmp_path / "chunked"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert request.read() == b"firstsecond"
        return httpx2.Response(200, content=b"done")

    with (
        agentrec.session(path, mode="once") as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        assert (
            client.post(
                "https://example.test/chunked", content=ChunkedRequest()
            ).content
            == b"done"
        )
    with (
        agentrec.session(path, mode="none") as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        assert (
            client.post(
                "https://example.test/chunked", content=ChunkedRequest()
            ).content
            == b"done"
        )
    assert calls == 1


def test_async_openai_stream_replays_parsed_chunks(tmp_path: Path) -> None:
    path = tmp_path / "async-sse"
    calls = 0
    event = {
        "id": "chatcmpl-async",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "fake-model",
        "choices": [{"index": 0, "delta": {"content": "chunk"}, "finish_reason": None}],
    }
    body = b"data: " + json.dumps(event).encode() + b"\n\n" + b"data: [DONE]\n\n"

    async def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=body
        )

    async def invoke(mode: str) -> list[str | None]:
        async with agentrec.session(path, mode=mode) as rec:
            client = openai.AsyncOpenAI(
                api_key="test",
                base_url="https://example.test/v1",
                max_retries=0,
                http_client=httpx2.AsyncClient(
                    transport=rec.async_transport(httpx2.MockTransport(upstream))
                ),
            )
            try:
                stream = await client.chat.completions.create(
                    model="fake-model",
                    messages=[{"role": "user", "content": "stream"}],
                    stream=True,
                )
                return [chunk.choices[0].delta.content async for chunk in stream]
            finally:
                await client.close()

    assert asyncio.run(invoke("once")) == ["chunk"]
    assert asyncio.run(invoke("none")) == ["chunk"]
    assert calls == 1


@pytest.mark.parametrize("case", ["gzip", "binary", "timeout", "request_stream"])
def test_async_transport_traffic_parity(tmp_path: Path, case: str) -> None:
    path = tmp_path / case
    calls = 0
    payload = b"\xff\x00" if case == "binary" else b"firstsecond"

    async def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert await request.aread() == payload
        if case == "timeout":
            raise httpx2.ReadTimeout("fake timeout", request=request)
        if case == "gzip":
            return httpx2.Response(
                200,
                headers={"content-encoding": "gzip"},
                content=gzip.compress(payload),
            )
        return httpx2.Response(200, content=payload)

    async def chunks():
        yield b"first"
        yield b"second"

    async def invoke(mode: str) -> None:
        async with (
            agentrec.session(path, mode=mode) as rec,
            httpx2.AsyncClient(
                transport=rec.async_transport(httpx2.MockTransport(upstream))
            ) as client,
        ):
            if case == "timeout":
                with pytest.raises(httpx2.ReadTimeout, match="fake timeout"):
                    await client.post("https://example.test/edge", content=payload)
            else:
                response = await client.post(
                    "https://example.test/edge",
                    content=chunks() if case == "request_stream" else payload,
                )
                assert response.content == payload
                assert "content-encoding" not in response.headers

    asyncio.run(invoke("once"))
    asyncio.run(invoke("none"))
    assert calls == 1


def test_async_anthropic_stream_replays_events(tmp_path: Path) -> None:
    path = tmp_path / "async-anthropic"
    calls = 0
    events = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": "claude-test",
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 0},
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hello"},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    body = b"".join(
        b"event: "
        + name.encode()
        + b"\n"
        + b"data: "
        + json.dumps(data).encode()
        + b"\n\n"
        for name, data in events
    )

    async def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=body
        )

    async def invoke(mode: str) -> list[str]:
        async with agentrec.session(path, mode=mode) as rec:
            client = anthropic.AsyncAnthropic(
                api_key="test",
                base_url="https://example.test",
                max_retries=0,
                http_client=httpx2.AsyncClient(
                    transport=rec.async_transport(httpx2.MockTransport(upstream))
                ),
            )
            try:
                stream = await client.messages.create(
                    model="claude-test",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "stream"}],
                    stream=True,
                )
                return [event.type async for event in stream]
            finally:
                await client.close()

    assert asyncio.run(invoke("once")) == [name for name, _ in events]
    assert asyncio.run(invoke("none")) == [name for name, _ in events]
    assert calls == 1
