"""Offline field-tech demo remains an occurrence-correct SDK integration."""

from __future__ import annotations

from pathlib import Path

import agentrec
from agentrec.cassette.store import CassetteStore
from examples.field_tech_agent.run import FakeLLM, run_agent, run_demo


def test_demo_transcript_is_real_and_stable() -> None:
    lines = run_demo()
    assert len(lines) == 4
    assert lines[0] == (
        "record: Replace the IGN-9 igniter on furnace F-100. "
        "model_calls=3 work_order=True"
    )
    assert lines[1] == (
        "replay: Replace the IGN-9 igniter on furnace F-100. "
        "upstream_calls=0 work_order=False"
    )
    assert "first differing path /body" in lines[2]
    assert lines[3] == "diff: steps=7 changed=2 added=0 removed=0"


def test_demo_cassette_has_repeated_model_and_flaky_tool_occurrences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "field-tech"
    upstream = FakeLLM()
    with agentrec.session(path, mode="once") as rec:
        final = run_agent(
            rec,
            prompt="F-100 furnace has no heat",
            work_order_path=tmp_path / "record-order.txt",
            upstream=upstream,
        )
    assert final == "Replace the IGN-9 igniter on furnace F-100."
    _, interactions = CassetteStore(path).load()
    model_calls = [item for item in interactions if item.kind == "http"]
    assert len(model_calls) == 3
    assert len({item.key for item in model_calls}) == 1
    assert [item.occurrence for item in model_calls] == [0, 1, 2]
    searches = [
        item
        for item in interactions
        if item.kind == "tool" and item.request["name"] == "search_parts"
    ]
    assert [item.occurrence for item in searches] == [0, 1]
    assert [item.response["result"]["stock"] for item in searches] == [3, 0]

    replay_order = tmp_path / "replay-order.txt"
    forbidden = FakeLLM()
    with agentrec.session(path, mode="none") as rec:
        assert (
            run_agent(
                rec,
                prompt="F-100 furnace has no heat",
                work_order_path=replay_order,
                upstream=forbidden,
            )
            == final
        )
    assert forbidden.calls == 0
    assert not replay_order.exists()
