"""Occurrence queues, ordering, misses, and mode selection."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agentrec.cassette.model import Interaction
from agentrec.cassette.replay import ReplayIndex
from agentrec.errors import (
    ReplayExhaustedError,
    ReplayMissError,
    ReplayOrderError,
    UnplayedInteractionsError,
)
from agentrec.modes import RecordMode, resolve_mode


def item(
    seq: int,
    key: str,
    occurrence: int,
    result: str,
    *,
    name: str = "model",
) -> Interaction:
    return Interaction(
        seq=seq,
        kind="tool",
        key=key,
        occurrence=occurrence,
        key_inputs_redacted=False,
        request={"name": name, "arguments": {"prompt": "same"}},
        response={"result": result},
        started_at=datetime.now(UTC),
        duration_ms=1.0,
    )


def test_identical_requests_replay_first_second_third_then_exhaust() -> None:
    key = "a" * 64
    index = ReplayIndex([item(n, key, n, str(n + 1)) for n in range(3)])
    request = {"name": "model", "arguments": {"prompt": "same"}}
    assert [index.play(key, request).response for _ in range(3)] == [
        {"result": "1"},
        {"result": "2"},
        {"result": "3"},
    ]
    assert index.play_count == 3
    assert index.all_played
    with pytest.raises(ReplayExhaustedError, match="after 3 occurrences"):
        index.play(key, request)


def test_stateful_tool_uses_same_fifo_semantics() -> None:
    key = "b" * 64
    index = ReplayIndex(
        [
            item(0, key, 0, "part-a", name="search_parts"),
            item(1, key, 1, "part-b", name="search_parts"),
        ]
    )
    request = {"name": "search_parts", "arguments": {"prompt": "same"}}
    assert index.play(key, request).response == {"result": "part-a"}
    assert index.play(key, request).response == {"result": "part-b"}


def test_different_keys_can_play_in_reverse_order_unless_strict() -> None:
    first = item(0, "a" * 64, 0, "a", name="alpha")
    second = item(1, "b" * 64, 0, "b", name="beta")
    relaxed = ReplayIndex([first, second])
    relaxed.play(second.key, second.request)
    relaxed.play(first.key, first.request)
    assert relaxed.all_played
    strict = ReplayIndex([first, second], strict_order=True)
    with pytest.raises(ReplayOrderError, match="expected seq 0"):
        strict.play(second.key, second.request)
    assert strict.play_count == 0


def test_unplayed_interactions_are_reported() -> None:
    entries = [item(0, "a" * 64, 0, "a"), item(1, "b" * 64, 0, "b")]
    index = ReplayIndex(entries)
    index.play(entries[0].key, entries[0].request)
    with pytest.raises(UnplayedInteractionsError, match="seq: 1"):
        index.assert_all_played()


def test_miss_shows_closest_name_and_different_path() -> None:
    recorded = item(0, "a" * 64, 0, "yes")
    index = ReplayIndex([recorded])
    request = {"name": "model", "arguments": {"prompt": "changed"}}
    with pytest.raises(ReplayMissError, match="/arguments/prompt"):
        index.play("b" * 64, request)


def test_repeats_are_explicit_opt_in() -> None:
    entry = item(0, "a" * 64, 0, "one")
    index = ReplayIndex([entry], allow_playback_repeats=True)
    assert index.play(entry.key, entry.request).response == {"result": "one"}
    assert index.play(entry.key, entry.request).response == {"result": "one"}
    assert index.play_count == 2


def test_invalid_occurrence_is_rejected() -> None:
    with pytest.raises(ValueError, match="occurrence"):
        ReplayIndex([item(0, "a" * 64, 1, "wrong")])


@pytest.mark.parametrize("value", [mode.value for mode in RecordMode])
def test_all_modes_resolve(value: str) -> None:
    assert resolve_mode(value).value == value


def test_environment_overrides_only_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTREC_MODE", "none")
    assert resolve_mode() is RecordMode.NONE
    assert resolve_mode("all") is RecordMode.ALL
    monkeypatch.setenv("AGENTREC_MODE", "bad")
    with pytest.raises(ValueError, match="invalid agentrec mode"):
        resolve_mode()
