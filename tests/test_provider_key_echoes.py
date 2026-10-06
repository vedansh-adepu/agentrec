"""Synthetic provider key echoes must not survive recording or privacy checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx2
import pytest
from typer.testing import CliRunner

import agentrec
from agentrec.cassette.model import ErrorRecord
from agentrec.cassette.store import CassetteStore
from agentrec.cli import app
from agentrec.redaction import Redactor, privacy_findings, scrub

ECHOES = [
    ("sk-proj-" + "FAKE" * 8, "openai_key"),
    ("sk-proj-FAK" + "*" * 20 + "WXYZ", "openai_key"),
    ("sk-ant-" + "FAKE" * 8, "anthropic_key"),
    ("sk-ant-FAK" + "*" * 20 + "WXYZ", "anthropic_key"),
    ("sk-***", "openai_key"),
    ("sk-ant-***", "anthropic_key"),
]
IDS = [
    "openai-full",
    "openai-masked",
    "anthropic-full",
    "anthropic-masked",
    "openai-short-mask",
    "anthropic-short-mask",
]


@pytest.mark.parametrize("echo,rule", ECHOES, ids=IDS)
def test_provider_key_echo_is_removed_in_every_value_context(
    echo: str, rule: str
) -> None:
    active = Redactor()
    placeholder = f"[REDACTED:{rule}]"
    assert active.redact_text(echo) == placeholder
    assert (
        active.redact_text(f"Incorrect API key provided: {echo}.")
        == f"Incorrect API key provided: {placeholder}."
    )
    request = active.redact_request(
        {
            "url": "https://example.test/",
            "headers": {"Authorization": echo, "x-debug": echo},
            "body": echo,
        },
        kind="http",
    )
    response = active.redact_response(
        {"headers": {"x-debug": echo}, "body": {"error": {"message": echo}}},
        kind="http",
    )
    assert request["body"] == placeholder
    assert request["headers"] == {
        "Authorization": "[REDACTED:header]",
        "x-debug": placeholder,
    }
    assert response["body"]["error"]["message"] == placeholder
    assert response["headers"]["x-debug"] == placeholder
    assert active.redact_text(placeholder) == placeholder
    assert (
        active.redact_text("sk-demo and ordinary * punctuation")
        == "sk-demo and ordinary * punctuation"
    )


@pytest.mark.parametrize("echo,rule", ECHOES, ids=IDS)
def test_recorded_error_echo_is_redacted_before_both_files_are_written(
    tmp_path: Path, echo: str, rule: str
) -> None:
    path = tmp_path / "failed"

    def upstream(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            401, headers={"x-debug": echo}, json={"error": {"message": echo}}
        )

    with (
        pytest.raises(RuntimeError, match="synthetic rejection"),
        agentrec.session(path, mode="once") as rec,
    ):
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            response = client.post(
                "https://example.test/",
                headers={"authorization": echo, "x-debug": echo},
                json={"echo": echo},
            )
            # Live callers receive the original; only persisted values are redacted.
            assert response.json()["error"]["message"] == echo
        raise RuntimeError(f"synthetic rejection: {echo}")
    metadata, interactions = CassetteStore(path).load()
    assert metadata.redaction_policy_version == 2
    assert metadata.error is not None
    assert metadata.error.message == f"synthetic rejection: [REDACTED:{rule}]"
    for file in (path / "cassette.json", path / "interactions.jsonl"):
        assert "sk-" not in file.read_text(encoding="utf-8")
    assert not privacy_findings(interactions, metadata)
    result = CliRunner().invoke(
        app, ["validate", str(path), "--privacy", "--allow-failed", "--json"]
    )
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("echo,rule", ECHOES, ids=IDS)
def test_privacy_cli_flags_unscrubbed_provider_echoes_and_scrub_removes_them(
    tmp_path: Path, echo: str, rule: str
) -> None:
    path = tmp_path / "legacy-policy"
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
        client.post("https://example.test/", json={"prompt": "ordinary"})
    store = CassetteStore(path)
    metadata, interactions = store.load()
    item = interactions[0]
    request = {
        **item.request,
        "headers": {"x-debug": echo},
        "body": json.dumps({"echo": echo}),
    }
    response = {
        **item.response,
        "headers": {"x-debug": echo},
        "body": json.dumps({"error": {"message": echo}}),
    }
    poisoned = [
        item.model_copy(
            update={
                "request": request,
                "response": response,
                "key_inputs_redacted": True,
            }
        )
    ]
    raw = b"".join(
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        + b"\n"
        for record in poisoned
    )
    metadata = metadata.model_copy(
        update={
            "redaction_policy_version": 1,
            "status": "failed",
            "error": ErrorRecord(type="SyntheticError", message=echo),
            "content_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    store.save(metadata, poisoned, replace=True)
    runner = CliRunner()
    before = runner.invoke(
        app, ["validate", str(path), "--privacy", "--allow-failed", "--json"]
    )
    assert before.exit_code == 1
    errors = json.loads(before.output)["errors"]
    for location in (
        "/request/headers/x-debug",
        "/request/body",
        "/response/headers/x-debug",
        "/response/body",
        "/cassette/error",
    ):
        assert any(location in error and rule in error for error in errors), errors
    assert echo not in before.output
    assert scrub(path) == 1
    updated, records = store.load()
    assert updated.redaction_policy_version == 2
    assert not privacy_findings(records, updated)
    assert (
        runner.invoke(
            app, ["validate", str(path), "--privacy", "--allow-failed", "--json"]
        ).exit_code
        == 0
    )
