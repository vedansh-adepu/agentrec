import json
from pathlib import Path
import socket

import pytest
from typer.testing import CliRunner

from agentrec.cli import app


runner = CliRunner()


def test_record_command_exits_zero_and_creates_cassette(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    result = runner.invoke(
        app,
        ["record", "--run-path", str(run_path), "--expression", "2+3"],
    )

    assert result.exit_code == 0
    assert (run_path / "metadata.json").is_file()
    assert (run_path / "trace.jsonl").is_file()
    assert (run_path / "responses").is_dir()
    assert (run_path / "artifacts" / "final_output.txt").is_file()


def test_record_output_includes_final_output(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["record", "--run-path", str(tmp_path / "math_run"), "--expression", "2+3"],
    )

    assert result.exit_code == 0
    assert "Recorded math flow." in result.output
    assert "final_output: 5" in result.output


def test_record_refuses_to_overwrite_existing_cassette_without_force(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    first = runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    second = runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+4"])

    assert first.exit_code == 0
    assert second.exit_code == 1
    assert "Use --force to overwrite it" in second.output


def test_record_force_overwrites_existing_cassette(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(
        app,
        ["record", "--run-path", str(run_path), "--expression", "2+4", "--force"],
    )

    assert result.exit_code == 0
    assert "final_output: 6" in result.output
    assert len((run_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()) == 3


def test_replay_command_exits_zero_after_recording(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"

    record_result = runner.invoke(
        app,
        ["record", "--run-path", str(run_path), "--expression", "2+3"],
    )
    replay_result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+3"],
    )

    assert record_result.exit_code == 0
    assert replay_result.exit_code == 0


def test_replay_output_includes_final_output(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+3"],
    )

    assert result.exit_code == 0
    assert "Replayed math flow." in result.output
    assert "final_output: 5" in result.output


def test_replay_with_changed_expression_exits_nonzero(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+4"],
    )

    assert result.exit_code == 1


def test_replay_miss_output_includes_clear_message(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+4"],
    )

    assert "Replay miss:" in result.output


def test_show_command_exits_zero_after_recording(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["show", "--run-path", str(run_path)])

    assert result.exit_code == 0


def test_show_output_includes_metadata_and_step_count(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["show", "--run-path", str(run_path)])

    assert "run_id: math_flow" in result.output
    assert "task: Calculate 2+3" in result.output
    assert "final_output: 5" in result.output
    assert "step_count: 3" in result.output


def test_show_output_includes_step_kinds(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["show", "--run-path", str(run_path)])

    assert "kind: model" in result.output
    assert "kind: tool" in result.output
    assert "kind: final" in result.output


def test_show_json_outputs_machine_readable_summary(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["show", "--run-path", str(run_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run"]["run_id"] == "math_flow"
    assert payload["run"]["schema_version"] == "1"
    assert payload["step_count"] == 3
    assert [step["kind"] for step in payload["steps"]] == ["model", "tool", "final"]


def test_show_command_is_read_only(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])
    before = _snapshot(run_path)

    result = runner.invoke(app, ["show", "--run-path", str(run_path)])

    assert result.exit_code == 0
    assert _snapshot(run_path) == before


def test_show_on_missing_cassette_exits_nonzero_with_clear_message(tmp_path: Path) -> None:
    result = runner.invoke(app, ["show", "--run-path", str(tmp_path / "missing_run")])

    assert result.exit_code == 1
    assert "Cassette error:" in result.output


def test_diff_command_exits_zero_for_valid_cassettes(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    runner.invoke(app, ["record", "--run-path", str(left), "--expression", "2+3"])
    runner.invoke(app, ["record", "--run-path", str(right), "--expression", "2+3"])

    result = runner.invoke(app, ["diff", "--left", str(left), "--right", str(right)])

    assert result.exit_code == 0


def test_diff_output_includes_changed_status(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    runner.invoke(app, ["record", "--run-path", str(left), "--expression", "2+3"])
    runner.invoke(app, ["record", "--run-path", str(right), "--expression", "2+3"])

    result = runner.invoke(app, ["diff", "--left", str(left), "--right", str(right)])

    assert "Cassette diff." in result.output
    assert "changed: False" in result.output


def test_diff_output_detects_final_output_difference(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    runner.invoke(app, ["record", "--run-path", str(left), "--expression", "2+3"])
    runner.invoke(app, ["record", "--run-path", str(right), "--expression", "2+4"])

    result = runner.invoke(app, ["diff", "--left", str(left), "--right", str(right)])

    assert result.exit_code == 0
    assert "final_output_changed: True" in result.output
    assert "changed: True" in result.output


def test_diff_json_outputs_machine_readable_summary(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    runner.invoke(app, ["record", "--run-path", str(left), "--expression", "2+3"])
    runner.invoke(app, ["record", "--run-path", str(right), "--expression", "2+4"])

    result = runner.invoke(app, ["diff", "--left", str(left), "--right", str(right), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["final_output_changed"] is True
    assert payload["changed"] is True


def test_diff_on_missing_cassette_exits_nonzero_with_clear_message(tmp_path: Path) -> None:
    left = tmp_path / "left"
    runner.invoke(app, ["record", "--run-path", str(left), "--expression", "2+3"])

    result = runner.invoke(
        app,
        ["diff", "--left", str(left), "--right", str(tmp_path / "missing")],
    )

    assert result.exit_code == 1
    assert "Cassette error:" in result.output


def test_validate_command_exits_zero_for_valid_cassette(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["validate", "--run-path", str(run_path)])

    assert result.exit_code == 0


def test_validate_output_includes_ok_true(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["validate", "--run-path", str(run_path)])

    assert "Cassette validation." in result.output
    assert "ok: True" in result.output
    assert "schema_version: 1" in result.output


def test_validate_json_outputs_machine_readable_summary(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    runner.invoke(app, ["record", "--run-path", str(run_path), "--expression", "2+3"])

    result = runner.invoke(app, ["validate", "--run-path", str(run_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1"
    assert payload["step_count"] == 3


def test_validate_on_missing_cassette_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "--run-path", str(tmp_path / "missing_run")])

    assert result.exit_code == 1


def test_validate_on_missing_cassette_outputs_error_text(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "--run-path", str(tmp_path / "missing_run")])

    assert "ok: False" in result.output
    assert "Missing cassette path" in result.output


def test_cli_commands_introduce_no_live_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_path = tmp_path / "math_run"
    other_run_path = tmp_path / "math_run_other"

    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)

    record_result = runner.invoke(
        app,
        ["record", "--run-path", str(run_path), "--expression", "2+3"],
    )
    other_record_result = runner.invoke(
        app,
        ["record", "--run-path", str(other_run_path), "--expression", "2+3"],
    )
    replay_result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+3"],
    )
    show_result = runner.invoke(app, ["show", "--run-path", str(run_path)])
    diff_result = runner.invoke(
        app,
        ["diff", "--left", str(run_path), "--right", str(other_run_path)],
    )
    validate_result = runner.invoke(app, ["validate", "--run-path", str(run_path)])

    assert record_result.exit_code == 0
    assert other_record_result.exit_code == 0
    assert replay_result.exit_code == 0
    assert show_result.exit_code == 0
    assert diff_result.exit_code == 0
    assert validate_result.exit_code == 0


def _snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(file_path.relative_to(path)): file_path.read_bytes()
        for file_path in sorted(path.rglob("*"))
        if file_path.is_file()
    }
