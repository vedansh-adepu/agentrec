from pathlib import Path
import socket

import pytest

from agentrec.errors import ReplayMissError
from agentrec.examples import record_math_flow, replay_math_flow
from agentrec.store import CassetteStore


def snapshot_files(path: Path) -> dict[Path, bytes]:
    return {
        file_path.relative_to(path): file_path.read_bytes()
        for file_path in sorted(path.rglob("*"))
        if file_path.is_file()
    }


def test_record_math_flow_creates_cassette(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    summary = record_math_flow(run_path)

    assert summary["mode"] == "record"
    assert (run_path / "metadata.json").is_file()
    assert (run_path / "trace.jsonl").is_file()
    assert (run_path / "responses").is_dir()
    assert (run_path / "artifacts" / "final_output.txt").is_file()


def test_replay_math_flow_returns_same_final_output(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    recorded = record_math_flow(run_path)
    replayed = replay_math_flow(run_path)

    assert replayed["mode"] == "replay"
    assert replayed["final_output"] == recorded["final_output"]


def test_replay_math_flow_returns_same_model_and_tool_output(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    recorded = record_math_flow(run_path, expression="17 * 23")
    replayed = replay_math_flow(run_path, expression="17 * 23")

    assert replayed["model_output"] == recorded["model_output"]
    assert replayed["tool_output"] == recorded["tool_output"]
    assert replayed["step_count"] == recorded["step_count"]


def test_cassette_has_expected_step_kinds(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    record_math_flow(run_path)

    steps = CassetteStore(run_path).read_steps()
    assert [step.kind for step in steps] == ["model", "tool", "final"]


def test_replay_does_not_mutate_cassette_files(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path)
    before = snapshot_files(run_path)

    replay_math_flow(run_path)

    assert snapshot_files(run_path) == before


def test_replay_with_changed_expression_raises_replay_miss(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, expression="2+3")

    with pytest.raises(ReplayMissError):
        replay_math_flow(run_path, expression="2+4")


def test_math_flow_introduces_no_live_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_path = tmp_path / "math_run"

    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)

    record_math_flow(run_path)
    replayed = replay_math_flow(run_path)

    assert replayed["final_output"] == "5"
