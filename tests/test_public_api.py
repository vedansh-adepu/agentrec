"""Freeze the supported import surface and its single version source."""

import agentrec


def test_public_api_surface_is_explicit_and_stable() -> None:
    assert set(agentrec.__all__) == {
        "AgentRecError",
        "MatchPolicy",
        "RecordMode",
        "Redactor",
        "ReplayExhaustedError",
        "ReplayMissError",
        "ReplayOrderError",
        "ReplayedToolError",
        "ReplayedTransportError",
        "Session",
        "UnplayedInteractionsError",
        "__version__",
        "legacy_async_httpx_transport",
        "legacy_httpx_transport",
        "session",
    }
    assert len(agentrec.__all__) == len(set(agentrec.__all__))
    assert all(hasattr(agentrec, name) for name in agentrec.__all__)
