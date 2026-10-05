"""Session lifecycle for deterministic HTTP and tool record/replay."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, ParamSpec, TypeVar

from .cassette.model import CassetteMetadata, ErrorRecord, Interaction, PolicyRecord
from .cassette.replay import ReplayIndex
from .cassette.store import CassetteOwnershipError, CassetteStore
from .errors import ReplayExhaustedError, ReplayMissError
from .matching import MatchPolicy
from .modes import RecordMode, resolve_mode
from .redaction import REDACTION_POLICY_VERSION, Redactor

P = ParamSpec("P")
R = TypeVar("R")


class Session:
    """Record or replay a single ordered cassette across HTTP and tool boundaries."""

    def __init__(
        self,
        path: str | Path,
        *,
        mode: RecordMode | str | None = None,
        match_policy: MatchPolicy | None = None,
        strict_order: bool = False,
        fail_on_unplayed: bool | None = None,
        allow_playback_repeats: bool = False,
        allow_failed: bool = False,
        allow_policy_mismatch: bool = False,
        redactor: Redactor | None = None,
    ) -> None:
        """Open a path under one mode and validate existing cassette integrity."""
        self.path = Path(path)
        self.mode = resolve_mode(mode)
        self.match_policy = match_policy or MatchPolicy()
        self.store = CassetteStore(self.path)
        self.redactor = redactor or Redactor()
        self._lock = threading.RLock()
        self._started = datetime.now(UTC)
        self._closed = False
        self._new: list[Interaction] = []
        self._existing: list[Interaction] = []
        self._metadata: CassetteMetadata | None = None
        self._occurrences: dict[str, int] = defaultdict(int)
        self.fail_on_unplayed = (
            self.mode is RecordMode.NONE
            if fail_on_unplayed is None
            else fail_on_unplayed
        )
        self._replay: ReplayIndex | None = None
        if self.mode is RecordMode.ALL:
            if self.path.exists() and any(self.path.iterdir()):
                self.store.require_owned()
        elif self.path.exists():
            metadata, interactions = self.store.load()
            if metadata.status == "failed" and not allow_failed:
                raise CassetteOwnershipError(
                    "failed cassette requires allow_failed=True"
                )
            policy = PolicyRecord.model_validate(self.match_policy.as_dict())
            if metadata.match_policy != policy and not allow_policy_mismatch:
                raise CassetteOwnershipError(
                    "cassette matching policy differs from session"
                )
            self._metadata = metadata
            self._existing = interactions
            self._replay = ReplayIndex(
                interactions,
                strict_order=strict_order,
                allow_playback_repeats=allow_playback_repeats,
            )
            for item in interactions:
                self._occurrences[item.key] += 1
        elif self.mode is RecordMode.NONE:
            raise ReplayMissError(f"cassette does not exist: {self.path}")

    @property
    def play_count(self) -> int:
        """Return the number of successful recorded-interaction playbacks."""
        return self._replay.play_count if self._replay else 0

    @property
    def all_played(self) -> bool:
        """Return whether every loaded interaction has played at least once."""
        return self._replay.all_played if self._replay else True

    def _lookup(self, key: str, request: dict[str, Any]) -> Interaction | None:
        if self._replay is None:
            return None
        with self._lock:
            try:
                return self._replay.play(key, request)
            except (ReplayMissError, ReplayExhaustedError):
                if self.mode is RecordMode.NEW_EPISODES:
                    return None
                raise

    def _key_inputs_changed(self, kind: str, key: str, request: dict[str, Any]) -> bool:
        if kind == "tool":
            return (
                self.match_policy.tool_key(request["name"], request["arguments"]) != key
            )
        body = request.get("body", "")
        if request.get("body_encoding") == "base64":
            raw = base64.b64decode(body)
        else:
            raw = str(body).encode("utf-8")
        return (
            self.match_policy.http_key(
                request["method"], request["url"], raw, request.get("headers", {})
            )
            != key
        )

    def _append(
        self,
        kind: Literal["http", "tool"],
        key: str,
        request: dict[str, Any],
        response: dict[str, Any] | None,
        error: ErrorRecord | None,
        started_at: datetime,
        duration_ms: float,
    ) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("session is closed")
            stored_request = self.redactor.redact_request(
                copy.deepcopy(request), kind=kind
            )
            stored_response = (
                self.redactor.redact_response(copy.deepcopy(response), kind=kind)
                if response is not None
                else None
            )
            stored_error = (
                ErrorRecord(
                    type=error.type,
                    message=self.redactor.redact_text(error.message),
                )
                if error is not None
                else None
            )
            item = Interaction(
                seq=len(self._existing) + len(self._new),
                kind=kind,
                key=key,
                occurrence=self._occurrences[key],
                key_inputs_redacted=self._key_inputs_changed(kind, key, stored_request),
                request=stored_request,
                response=stored_response,
                error=stored_error,
                started_at=started_at,
                duration_ms=duration_ms,
            )
            self._occurrences[key] += 1
            self._new.append(item)

    def _recording_allowed(self) -> bool:
        return (
            self.mode is RecordMode.ALL
            or self.mode is RecordMode.NEW_EPISODES
            or (self.mode is RecordMode.ONCE and self._replay is None)
        )

    def transport(self, inner: Any = None) -> Any:
        """Return an httpx2 transport for a sync SDK client."""
        from .transport.httpx2_transport import RecordReplayTransport

        return RecordReplayTransport(self, inner=inner)

    def async_transport(self, inner: Any = None) -> Any:
        """Return an httpx2 transport for an async SDK client."""
        from .transport.httpx2_transport import AsyncRecordReplayTransport

        return AsyncRecordReplayTransport(self, inner=inner)

    def tool(self, function: Callable[P, R]) -> Callable[P, R]:
        """Decorate a sync or async tool with argument snapshot and outcome replay."""
        from ._tool_decorator import decorate_tool

        return decorate_tool(self, function)

    def close(self, error: BaseException | None = None) -> None:
        """Finalize a writable session once and enforce optional play accounting."""
        if self._closed:
            return
        self._closed = True
        if self._recording_allowed():
            interactions = self._existing + self._new
            if self._new or self._metadata is None:
                data = b"".join(
                    json.dumps(
                        item.model_dump(mode="json"),
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                    + b"\n"
                    for item in interactions
                )
                from . import __version__

                metadata = CassetteMetadata(
                    agentrec_version=__version__,
                    match_policy=PolicyRecord.model_validate(
                        self.match_policy.as_dict()
                    ),
                    redaction_policy_version=REDACTION_POLICY_VERSION,
                    status="failed" if error else "complete",
                    created_at=self._metadata.created_at
                    if self._metadata
                    else self._started,
                    finalized_at=datetime.now(UTC),
                    interaction_count=len(interactions),
                    content_sha256=hashlib.sha256(data).hexdigest(),
                    error=(
                        ErrorRecord(
                            type=type(error).__name__,
                            message=self.redactor.redact_text(str(error)),
                        )
                        if error
                        else None
                    ),
                )
                self.store.save(
                    metadata,
                    interactions,
                    replace=self._metadata is not None or self.mode is RecordMode.ALL,
                )
        if self.fail_on_unplayed and self._replay and error is None:
            self._replay.assert_all_played()

    def __enter__(self) -> Session:
        """Return this open session for a sync with block."""
        return self

    def __exit__(
        self, exc_type: Any, exc: BaseException | None, traceback: Any
    ) -> None:
        """Finalize even if the wrapped agent failed."""
        self.close(error=exc)

    async def __aenter__(self) -> Session:
        """Return this open session for an async with block."""
        return self

    async def __aexit__(
        self, exc_type: Any, exc: BaseException | None, traceback: Any
    ) -> None:
        """Finalize even if the wrapped async agent failed."""
        self.close(error=exc)


def session(path: str | Path, **kwargs: Any) -> Session:
    """Open a cassette session with explicit or environment-selected mode."""
    return Session(path, **kwargs)
