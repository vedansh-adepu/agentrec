import json
from pathlib import Path

import pytest

from agentrec._legacy.diff import diff_cassettes
from agentrec._legacy.models import RunRecord, Step, Usage
from agentrec._legacy.store import CassetteStore
from agentrec.errors import CassetteError


def test_diff_cassettes_returns_unchanged_for_equivalent_cassettes(
    tmp_path: Path,
) -> None:
    left = _write_cassette(tmp_path / "left")
    right = _write_cassette(tmp_path / "right")

    result = diff_cassettes(left.path, right.path)

    assert result["changed"] is False
    assert result["final_output_changed"] is False
    assert result["step_count_changed"] is False
    assert result["step_sequence_changed"] is False
    json.dumps(result)


def test_diff_cassettes_detects_final_output_changes(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left", final_output="5")
    right = _write_cassette(tmp_path / "right", final_output="6")

    result = diff_cassettes(left.path, right.path)

    assert result["changed"] is True
    assert result["left_final_output"] == "5"
    assert result["right_final_output"] == "6"
    assert result["final_output_changed"] is True


def test_diff_cassettes_detects_step_count_changes(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")
    right_steps = _default_steps("5")
    right_steps.append(
        Step(
            index=3,
            kind="tool",
            name="extra_tool",
            latency_ms=1.0,
        ),
    )
    right = _write_cassette(tmp_path / "right", steps=right_steps)

    result = diff_cassettes(left.path, right.path)

    assert result["changed"] is True
    assert result["left_step_count"] == 3
    assert result["right_step_count"] == 4
    assert result["step_count_changed"] is True


def test_diff_cassettes_detects_step_sequence_changes(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")
    right_steps = [
        Step(index=0, kind="model", name="fake-math", latency_ms=10.0),
        Step(index=1, kind="tool", name="lookup", latency_ms=5.0),
        Step(index=2, kind="final", name="final_output"),
    ]
    right = _write_cassette(tmp_path / "right", steps=right_steps)

    result = diff_cassettes(left.path, right.path)

    assert result["changed"] is True
    assert result["left_step_sequence"] == [
        "model:fake-math",
        "tool:calculator",
        "final:final_output",
    ]
    assert result["right_step_sequence"] == [
        "model:fake-math",
        "tool:lookup",
        "final:final_output",
    ]
    assert result["step_sequence_changed"] is True


def test_diff_cassettes_returns_latency_totals(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")
    right = _write_cassette(
        tmp_path / "right",
        steps=[
            Step(index=0, kind="model", name="fake-math", latency_ms=20.0),
            Step(index=1, kind="tool", name="calculator", latency_ms=7.0),
            Step(index=2, kind="final", name="final_output"),
        ],
    )

    result = diff_cassettes(left.path, right.path)

    assert result["left_total_latency_ms"] == 15.0
    assert result["right_total_latency_ms"] == 27.0
    assert result["latency_delta_ms"] == 12.0


def test_diff_cassettes_returns_cost_totals_even_if_zero(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")
    right = _write_cassette(tmp_path / "right")

    result = diff_cassettes(left.path, right.path)

    assert result["left_total_cost_usd"] == 0.0
    assert result["right_total_cost_usd"] == 0.0
    assert result["cost_delta_usd"] == 0.0


def test_diff_cassettes_does_not_mutate_cassette_files(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")
    right = _write_cassette(tmp_path / "right")
    before = {
        "left": _snapshot(left.path),
        "right": _snapshot(right.path),
    }

    diff_cassettes(left.path, right.path)

    assert _snapshot(left.path) == before["left"]
    assert _snapshot(right.path) == before["right"]


def test_diff_cassettes_raises_cassette_error_for_missing_path(tmp_path: Path) -> None:
    left = _write_cassette(tmp_path / "left")

    with pytest.raises(CassetteError):
        diff_cassettes(left.path, tmp_path / "missing")


def _write_cassette(
    path: Path,
    *,
    run_id: str = "run",
    task: str = "Calculate 2+3",
    final_output: str = "5",
    steps: list[Step] | None = None,
) -> CassetteStore:
    store = CassetteStore(path)
    run = RunRecord(run_id=run_id, task=task, final_output=final_output)
    store.initialize(run)
    store.write_final_output(final_output)
    for step in steps or _default_steps(final_output):
        store.append_step(step)
    return store


def _default_steps(final_output: str) -> list[Step]:
    return [
        Step(
            index=0,
            kind="model",
            name="fake-math",
            latency_ms=10.0,
            usage=Usage(cost_usd=0.0),
        ),
        Step(index=1, kind="tool", name="calculator", latency_ms=5.0),
        Step(
            index=2,
            kind="final",
            name="final_output",
            output={"content": final_output},
        ),
    ]


def _snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(file_path.relative_to(path)): file_path.read_bytes()
        for file_path in sorted(path.rglob("*"))
        if file_path.is_file()
    }
