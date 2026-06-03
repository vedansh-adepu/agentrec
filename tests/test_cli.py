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


def test_show_on_missing_cassette_exits_nonzero_with_clear_message(tmp_path: Path) -> None:
    result = runner.invoke(app, ["show", "--run-path", str(tmp_path / "missing_run")])

    assert result.exit_code == 1
    assert "Cassette error:" in result.output


def test_cli_commands_introduce_no_live_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_path = tmp_path / "math_run"

    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)

    record_result = runner.invoke(
        app,
        ["record", "--run-path", str(run_path), "--expression", "2+3"],
    )
    replay_result = runner.invoke(
        app,
        ["replay", "--run-path", str(run_path), "--expression", "2+3"],
    )
    show_result = runner.invoke(app, ["show", "--run-path", str(run_path)])

    assert record_result.exit_code == 0
    assert replay_result.exit_code == 0
    assert show_result.exit_code == 0


@pytest.mark.parametrize("command", ["diff", "validate"])
def test_cli_does_not_implement_future_commands(command: str) -> None:
    result = runner.invoke(app, [command])

    assert result.exit_code != 0
