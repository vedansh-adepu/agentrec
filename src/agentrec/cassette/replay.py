"""Occurrence-correct, per-key FIFO replay of cassette interactions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from agentrec.errors import (
    ReplayExhaustedError,
    ReplayMissError,
    ReplayOrderError,
    UnplayedInteractionsError,
)

from .model import Interaction


def _summary(request: dict[str, Any]) -> str:
    if "method" in request:
        return f"{request.get('method')} {request.get('url')}"
    if "name" in request:
        return f"tool {request.get('name')}"
    return "request"


def _first_difference(left: Any, right: Any, path: str = "") -> str | None:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            child = f"{path}/{key}"
            if key not in left or key not in right:
                return child
            difference = _first_difference(left[key], right[key], child)
            if difference is not None:
                return difference
        return None
    if isinstance(left, list) and isinstance(right, list):
        for index, (a, b) in enumerate(zip(left, right, strict=False)):
            difference = _first_difference(a, b, f"{path}/{index}")
            if difference is not None:
                return difference
        if len(left) != len(right):
            return f"{path}/{min(len(left), len(right))}"
        return None
    if left != right:
        return path or "/"
    return None


class ReplayIndex:
    """Serve each key's interactions once, in their recorded occurrence order."""

    def __init__(
        self,
        interactions: Sequence[Interaction],
        *,
        strict_order: bool = False,
        allow_playback_repeats: bool = False,
    ) -> None:
        """Index a contiguous recording and reject inconsistent occurrences."""
        self.interactions = list(interactions)
        self.strict_order = strict_order
        self.allow_playback_repeats = allow_playback_repeats
        self._by_key: dict[str, list[Interaction]] = defaultdict(list)
        self._next: dict[str, int] = defaultdict(int)
        self._played: set[int] = set()
        self._play_count = 0
        self._global_next = 0
        for seq, item in enumerate(self.interactions):
            if item.seq != seq:
                raise ValueError("replay interactions must have contiguous seq values")
            expected = len(self._by_key[item.key])
            if item.occurrence != expected:
                raise ValueError(
                    f"occurrence for key {item.key} must be {expected}, "
                    f"got {item.occurrence}"
                )
            self._by_key[item.key].append(item)

    @property
    def play_count(self) -> int:
        """Return the total number of successful playback calls."""
        return self._play_count

    @property
    def all_played(self) -> bool:
        """Return whether each recorded interaction has played at least once."""
        return len(self._played) == len(self.interactions)

    @property
    def unplayed(self) -> list[Interaction]:
        """Return the recorded interactions that have not played."""
        return [item for item in self.interactions if item.seq not in self._played]

    def assert_all_played(self) -> None:
        """Raise with unused sequence numbers if playback was incomplete."""
        if self.unplayed:
            numbers = ", ".join(str(item.seq) for item in self.unplayed)
            raise UnplayedInteractionsError(f"unplayed interactions at seq: {numbers}")

    def _miss_message(self, request: dict[str, Any]) -> str:
        summary = _summary(request)
        candidates = [
            item
            for item in self.interactions
            if item.kind == ("http" if "method" in request else "tool")
            and _summary(item.request) == summary
        ][:3]
        if not candidates:
            return f"replay miss for {summary}; no similar recorded request"
        examples = "; ".join(
            f"seq {item.seq} first differing path "
            f"{_first_difference(item.request, request) or '(none)'}"
            for item in candidates
        )
        return f"replay miss for {summary}; closest recorded: {examples}"

    def play(self, key: str, request: dict[str, Any]) -> Interaction:
        """Return the next occurrence for a key or raise a typed replay error."""
        queue = self._by_key.get(key)
        if queue is None:
            raise ReplayMissError(self._miss_message(request))
        offset = self._next[key]
        if offset >= len(queue):
            if not self.allow_playback_repeats:
                raise ReplayExhaustedError(
                    f"replay exhausted for {_summary(request)} "
                    f"after {len(queue)} occurrences"
                )
            offset = 0
        item = queue[offset]
        if self.strict_order and item.seq != self._global_next:
            raise ReplayOrderError(
                f"strict replay order expected seq {self._global_next}, got {item.seq}"
            )
        self._next[key] = offset + 1
        self._played.add(item.seq)
        self._play_count += 1
        if self.strict_order:
            self._global_next += 1
        return item
