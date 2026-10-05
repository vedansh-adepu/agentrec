"""Recording and replay mode selection."""

from __future__ import annotations

import os
from enum import StrEnum


class RecordMode(StrEnum):
    """Choose replay-only, record-once, append-misses, or replace-all behavior."""

    NONE = "none"
    ONCE = "once"
    NEW_EPISODES = "new_episodes"
    ALL = "all"


def resolve_mode(mode: RecordMode | str | None = None) -> RecordMode:
    """Resolve a default mode, honoring AGENTREC_MODE only when unspecified."""
    selected = (
        mode if mode is not None else os.getenv("AGENTREC_MODE", RecordMode.ONCE.value)
    )
    try:
        return RecordMode(selected)
    except ValueError as exc:
        raise ValueError(f"invalid agentrec mode: {selected!r}") from exc
