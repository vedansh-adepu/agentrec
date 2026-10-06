"""Schema-v2 validation catches structural, integrity, and privacy defects."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import agentrec
from agentrec.cassette.store import CassetteStoreError
from agentrec.validation import ValidationLevel, validate_v2_cassette


def record_tool(path: Path) -> None:
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def lookup(value: int) -> int:
            return value * 2

        assert lookup(3) == 6


def mutate_interaction(path: Path, change: object, *, fix_digest: bool) -> None:
    interactions_path = path / "interactions.jsonl"
    entries = [
        json.loads(line)
        for line in interactions_path.read_text(encoding="utf-8").splitlines()
    ]
    change(entries[0])
    data = b"".join(
        json.dumps(entry, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for entry in entries
    )
    interactions_path.write_bytes(data)
    if fix_digest:
        metadata_path = path / "cassette.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["content_sha256"] = hashlib.sha256(data).hexdigest()
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8", newline="\n")


def test_pristine_cassette_passes_every_level(tmp_path: Path) -> None:
    path = tmp_path / "good"
    record_tool(path)
    for level in ValidationLevel:
        result = validate_v2_cassette(path, level=level)
        assert result["ok"], result["errors"]
        assert result["interaction_count"] == 1


def test_tampered_response_fails_digest_and_session_load(tmp_path: Path) -> None:
    path = tmp_path / "tampered"
    record_tool(path)
    mutate_interaction(
        path, lambda entry: entry["response"].update(result=999), fix_digest=False
    )
    assert not validate_v2_cassette(path, level="integrity")["ok"]
    with pytest.raises(CassetteStoreError, match="integrity"):
        agentrec.session(path, mode="none")


def test_request_edit_with_recomputed_digest_still_fails_key(tmp_path: Path) -> None:
    path = tmp_path / "edited-request"
    record_tool(path)
    mutate_interaction(
        path,
        lambda entry: entry["request"]["arguments"].update(value=99),
        fix_digest=True,
    )
    result = validate_v2_cassette(path, level="integrity")
    assert any("key does not match" in error for error in result["errors"])


@pytest.mark.parametrize(
    "change",
    [
        lambda entry: entry.update(response=None),
        lambda entry: entry["response"].update(unknown=1),
        lambda entry: entry.update(seq=5),
    ],
)
def test_missing_or_malformed_interaction_fails_structural(
    tmp_path: Path, change: object
) -> None:
    path = tmp_path / "invalid"
    record_tool(path)
    mutate_interaction(path, change, fix_digest=True)
    result = validate_v2_cassette(path, level="structural")
    assert not result["ok"]


def test_wrong_typed_http_response_fails_structural(tmp_path: Path) -> None:
    import httpx2

    path = tmp_path / "typed-http"
    with (
        agentrec.session(path, mode="once") as rec,
        httpx2.Client(
            transport=rec.transport(
                httpx2.MockTransport(
                    lambda request: httpx2.Response(200, json={"ok": True})
                )
            )
        ) as client,
    ):
        client.get("https://example.test/")
    mutate_interaction(
        path, lambda entry: entry["response"].update(status="200"), fix_digest=True
    )
    assert not validate_v2_cassette(path, level="structural")["ok"]


def test_bad_occurrence_and_count_fail_integrity(tmp_path: Path) -> None:
    path = tmp_path / "occurrence"
    record_tool(path)
    mutate_interaction(path, lambda entry: entry.update(occurrence=1), fix_digest=True)
    assert not validate_v2_cassette(path, level="integrity")["ok"]


def test_failed_run_needs_explicit_allow_failed(tmp_path: Path) -> None:
    path = tmp_path / "failed"
    with pytest.raises(RuntimeError), agentrec.session(path, mode="once"):
        raise RuntimeError("failure")
    assert validate_v2_cassette(path, level="integrity")["ok"]
    assert not validate_v2_cassette(path, level="replayable")["ok"]
    assert validate_v2_cassette(path, level="replayable", allow_failed=True)["ok"]


def test_privacy_level_finds_secret_even_with_updated_digest(tmp_path: Path) -> None:
    path = tmp_path / "private"
    record_tool(path)
    mutate_interaction(
        path,
        lambda entry: entry["response"].update(result="sk-" + "F" * 24),
        fix_digest=True,
    )
    assert validate_v2_cassette(path, level="replayable")["ok"]
    result = validate_v2_cassette(path)
    assert not result["ok"]
    assert any("openai_key" in error for error in result["errors"])


def test_redacted_key_reports_unverifiable_scope(tmp_path: Path) -> None:
    path = tmp_path / "redacted"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def echo(value: str) -> str:
            return value

        echo("sk-" + "G" * 24)
    result = validate_v2_cassette(path)
    assert result["ok"], result["errors"]
    assert result["unverifiable_key_count"] == 1
    assert any("cannot be recomputed" in warning for warning in result["warnings"])


def test_v2_cli_validate_and_show_use_validation(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from agentrec.cli import app

    runner = CliRunner()
    path = tmp_path / "cli"
    record_tool(path)
    valid = runner.invoke(app, ["validate", str(path), "--json"])
    assert valid.exit_code == 0
    assert json.loads(valid.output)["ok"]
    shown = runner.invoke(app, ["show", str(path), "--json"])
    assert shown.exit_code == 0
    assert json.loads(shown.output)["interaction_count"] == 1
    mutate_interaction(path, lambda entry: entry.update(seq=3), fix_digest=True)
    invalid = runner.invoke(app, ["validate", str(path), "--level", "structural"])
    assert invalid.exit_code == 1
    hidden = runner.invoke(app, ["show", str(path)])
    assert hidden.exit_code == 2
