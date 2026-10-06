"""Schema-v2 trajectory diff detects intermediate behavior drift."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

import agentrec
from agentrec.cli import app
from agentrec.diff import diff_v2_cassettes


def record(path: Path, prompt: str, result: str, *, extra: bool = False) -> None:
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def model(prompt: str) -> str:
            return result

        assert model(prompt) == result
        if extra:

            @rec.tool
            def lookup(value: int) -> int:
                return value + 1

            lookup(1)


def test_changed_prompt_with_identical_result_is_detected(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "old prompt", "same answer")
    record(right, "new prompt", "same answer")
    result = diff_v2_cassettes(left, right)
    assert result["behavior_changed"]
    assert result["changed"] == 1
    assert result["added"] == result["removed"] == 0
    paths = result["details"][0]["request_paths"]
    assert any(item["path"] == "/arguments/prompt" for item in paths)
    assert result["details"][0]["response_paths"] == []


def test_response_change_is_detected(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "prompt", "old")
    record(right, "prompt", "new")
    result = diff_v2_cassettes(left, right)
    assert result["changed"] == 1
    assert any(
        item["path"] == "/result" for item in result["details"][0]["response_paths"]
    )


def test_added_step_is_aligned_by_key_and_occurrence(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "prompt", "answer")
    record(right, "prompt", "answer", extra=True)
    result = diff_v2_cassettes(left, right)
    assert result["added"] == 1
    assert result["removed"] == result["changed"] == 0


def test_duration_delta_does_not_count_as_behavior_change(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "prompt", "answer")
    record(right, "prompt", "answer")
    file = right / "interactions.jsonl"
    entry = json.loads(file.read_text(encoding="utf-8"))
    entry["duration_ms"] += 100
    data = (json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n").encode()
    file.write_bytes(data)
    metadata_file = right / "cassette.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata["content_sha256"] = hashlib.sha256(data).hexdigest()
    metadata_file.write_text(json.dumps(metadata), encoding="utf-8", newline="\n")
    result = diff_v2_cassettes(left, right)
    assert not result["behavior_changed"]
    assert result["changed"] == 0
    assert result["duration_delta_ms"] > 0


def test_cli_json_and_fail_on_change(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "old", "same")
    record(right, "new", "same")
    result = CliRunner().invoke(
        app,
        [
            "diff",
            str(left),
            str(right),
            "--json",
            "--fail-on-change",
        ],
    )
    assert result.exit_code == 1
    assert json.loads(result.output)["changed"] == 1


def test_cli_refuses_structurally_invalid_v2_cassette(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    record(left, "prompt", "answer")
    record(right, "prompt", "answer")
    (right / "interactions.jsonl").write_text(
        "not json\n", encoding="utf-8", newline="\n"
    )
    result = CliRunner().invoke(app, ["diff", str(left), str(right)])
    assert result.exit_code == 2
    assert "error:" in result.output
