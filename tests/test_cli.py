"""Schema-v2 CLI behavior and safe failure regressions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import agentrec
from agentrec.cassette.store import CassetteOwnershipError
from agentrec.cli import app

runner = CliRunner()


def cassette(path: Path, *, prompt: str = "original", result: str = "ok") -> None:
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def lookup(prompt: str) -> str:
            return result

        assert lookup(prompt) == result


def test_version_command_and_global_option() -> None:
    command = runner.invoke(app, ["version"])
    option = runner.invoke(app, ["--version"])
    assert command.exit_code == option.exit_code == 0
    assert command.output.strip() == option.output.strip() == agentrec.__version__


def test_show_json_and_text(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    structured = runner.invoke(app, ["show", str(path), "--json"])
    assert structured.exit_code == 0
    assert json.loads(structured.output)["interaction_count"] == 1
    text = runner.invoke(app, ["show", str(path)])
    assert text.exit_code == 0
    assert "occurrence=0" in text.output


def test_validate_levels_and_check_failure_exit(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    good = runner.invoke(app, ["validate", str(path), "--level", "integrity"])
    assert good.exit_code == 0
    (path / "interactions.jsonl").write_text("broken\n", encoding="utf-8", newline="\n")
    bad = runner.invoke(app, ["validate", str(path), "--json"])
    assert bad.exit_code == 1
    assert not json.loads(bad.output)["ok"]


def test_scrub_refuses_unowned_directory_without_deleting_anything(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unrelated"
    path.mkdir()
    precious = path / "precious.txt"
    precious.write_text("do not delete", encoding="utf-8", newline="\n")
    result = runner.invoke(app, ["scrub", str(path)])
    assert result.exit_code == 2
    assert result.output.startswith("error:")
    assert precious.read_text(encoding="utf-8") == "do not delete"


def test_scrub_owned_cassette(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    result = runner.invoke(app, ["scrub", str(path)])
    assert result.exit_code == 0
    assert "scrubbed interactions: 0" in result.output


def test_inspect_miss_explains_changed_tool_argument(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "kind": "tool",
                "name": "lookup",
                "arguments": {"prompt": "changed"},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    result = runner.invoke(app, ["inspect-miss", str(path), str(request)])
    assert result.exit_code == 1
    assert result.output.startswith("error:")
    assert "/arguments/prompt" in result.output


def test_inspect_miss_reports_match(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "kind": "tool",
                "name": "lookup",
                "arguments": {"prompt": "original"},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    result = runner.invoke(app, ["inspect-miss", str(path), str(request)])
    assert result.exit_code == 0
    assert "match: seq=0 occurrence=0" in result.output


def test_expected_input_error_has_no_traceback(tmp_path: Path) -> None:
    result = runner.invoke(app, ["show", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert result.output.startswith("error:")
    assert "Traceback" not in result.output


def test_old_math_commands_are_removed() -> None:
    assert runner.invoke(app, ["record"]).exit_code != 0
    assert runner.invoke(app, ["replay"]).exit_code != 0


def test_validate_text_failure_and_bad_level_are_one_line(tmp_path: Path) -> None:
    path = tmp_path / "run"
    cassette(path)
    invalid_level = runner.invoke(
        app, ["validate", str(path), "--level", "not-a-level"]
    )
    assert invalid_level.exit_code == 2
    assert invalid_level.output.startswith("error:")
    (path / "interactions.jsonl").write_text("broken\n", encoding="utf-8", newline="\n")
    invalid_cassette = runner.invoke(app, ["validate", str(path)])
    assert invalid_cassette.exit_code == 1
    assert invalid_cassette.output.startswith("error:")
    assert len(invalid_cassette.output.splitlines()) == 1


def test_mode_all_refuses_non_cassette_without_deleting(tmp_path: Path) -> None:
    path = tmp_path / "unrelated"
    path.mkdir()
    important = path / "important.txt"
    important.write_text("keep", encoding="utf-8", newline="\n")
    with pytest.raises(CassetteOwnershipError):
        agentrec.session(path, mode="all")
    assert important.read_text(encoding="utf-8") == "keep"
