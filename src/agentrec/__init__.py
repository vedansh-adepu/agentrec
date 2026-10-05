"""agentrec: deterministic record-and-replay for AI-agent runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

__version__ = "0.1.0"


from .session import Session, session

__all__ = [
    "Session",
    "__version__",
    "legacy_async_httpx_transport",
    "legacy_httpx_transport",
    "session",
]


def legacy_httpx_transport(
    session: Session, inner: httpx.BaseTransport | None = None
) -> httpx.BaseTransport:
    """Return an optional legacy httpx sync transport for an agentrec session."""
    try:
        from .transport.httpx_transport import RecordReplayTransport
    except ImportError as exc:
        raise ImportError("install agentrec[httpx] for legacy httpx transport") from exc
    return RecordReplayTransport(session, inner=inner)


def legacy_async_httpx_transport(
    session: Session, inner: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncBaseTransport:
    """Return an optional legacy httpx async transport for an agentrec session."""
    try:
        from .transport.httpx_transport import AsyncRecordReplayTransport
    except ImportError as exc:
        raise ImportError("install agentrec[httpx] for legacy httpx transport") from exc
    return AsyncRecordReplayTransport(session, inner=inner)
