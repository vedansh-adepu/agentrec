"""Pre-persistence privacy regressions for schema-v2 sessions."""

from __future__ import annotations

from pathlib import Path

import httpx2

import agentrec
from agentrec.cassette.store import CassetteStore
from agentrec.redaction import Redactor, privacy_findings, scrub


def test_secrets_never_enter_cassette_files(tmp_path: Path) -> None:
    path = tmp_path / "secrets"
    fake_openai = "sk-" + "A" * 24
    fake_anthropic = "sk-ant-" + "B" * 24
    fake_aws = "AKIA" + "C" * 16
    fake_github = "ghp_" + "D" * 24

    def upstream(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"set-cookie": "session=private"},
            json={"answer": fake_aws, "token": fake_github},
        )

    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def echo(value: str) -> str:
            return fake_github + value

        assert echo(fake_anthropic).endswith(fake_anthropic)
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            response = client.post(
                "https://example.test/api?api_key=plain-query-secret",
                headers={"Authorization": "Bearer " + fake_openai},
                json={"message": fake_openai},
            )
            assert response.json()["answer"] == fake_aws

    disk = (path / "cassette.json").read_text() + (
        path / "interactions.jsonl"
    ).read_text()
    for secret in (
        fake_openai,
        fake_anthropic,
        fake_aws,
        fake_github,
        "plain-query-secret",
        "session=private",
    ):
        assert secret not in disk
    assert "[REDACTED:" in disk
    _, interactions = CassetteStore(path).load()
    assert not privacy_findings(interactions)
    tool, http = interactions
    assert tool.key_inputs_redacted
    assert http.key_inputs_redacted
    with agentrec.session(path, mode="none") as rec:

        @rec.tool
        def echo(value: str) -> str:
            raise AssertionError("tool executed")

        assert echo(fake_anthropic) == "[REDACTED:github_token][REDACTED:anthropic_key]"
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            response = client.post(
                "https://example.test/api?api_key=plain-query-secret",
                headers={"Authorization": "Bearer " + fake_openai},
                json={"message": fake_openai},
            )
            assert response.json()["answer"] == "[REDACTED:aws_key]"


def test_header_secret_does_not_change_default_match_key(tmp_path: Path) -> None:
    path = tmp_path / "headers"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json={"ok": True})

    with (
        agentrec.session(path, mode="once") as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        client.get(
            "https://example.test/",
            headers={"authorization": "Bearer topsecret123"},
        )
    _, interactions = CassetteStore(path).load()
    assert not interactions[0].key_inputs_redacted
    with (
        agentrec.session(path, mode="none") as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        assert client.get(
            "https://example.test/",
            headers={"authorization": "Bearer changedsecret456"},
        ).json() == {"ok": True}
    assert calls == 1


def test_custom_rules_hooks_email_and_entropy_are_opt_in() -> None:
    plain = Redactor()
    email = "person@example.test"
    assert plain.redact_text(email) == email
    custom = Redactor(
        custom_patterns={"internal": r"CUSTOM-[0-9]+"},
        redact_email=True,
        before_record_tool=lambda value: {**value, "extra": "CUSTOM-123"},
    )
    result = custom.redact_request(
        {"name": "tool", "arguments": {"email": email}},
        kind="tool",
    )
    assert result["arguments"]["email"] == "[REDACTED:email]"
    assert result["extra"] == "[REDACTED:internal]"
    entropy = Redactor(entropy_threshold=3.0)
    assert "[REDACTED:entropy]" in entropy.redact_text(
        "abcdefghijklmnopqrstuvwxyz0123456789"
    )


def test_scrub_reapplies_new_rules_and_updates_digest(tmp_path: Path) -> None:
    path = tmp_path / "scrub"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def lookup(value: str) -> str:
            return value

        assert lookup("CUSTOM-123") == "CUSTOM-123"
    before = (path / "interactions.jsonl").read_text()
    assert "CUSTOM-123" in before
    changed = scrub(path, Redactor(custom_patterns={"internal": r"CUSTOM-[0-9]+"}))
    assert changed == 1
    assert "CUSTOM-123" not in (path / "interactions.jsonl").read_text()
    metadata, interactions = CassetteStore(path).load()
    assert metadata.interaction_count == 1
    assert interactions[0].key_inputs_redacted
    assert scrub(path, Redactor(custom_patterns={"internal": r"CUSTOM-[0-9]+"})) == 0


def test_privacy_scanner_finds_built_in_pattern(tmp_path: Path) -> None:
    path = tmp_path / "find"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def plain(value: str) -> str:
            return value

        plain("ordinary")
    _, interactions = CassetteStore(path).load()
    poisoned = interactions[0].model_copy(
        update={"response": {"result": "sk-" + "E" * 24}}
    )
    findings = privacy_findings([poisoned])
    assert any("openai_key" in finding for finding in findings)


def test_failed_session_error_is_redacted_before_metadata_write(
    tmp_path: Path,
) -> None:
    import pytest

    path = tmp_path / "failed-secret"
    fake = "sk-" + "Z" * 24
    with pytest.raises(RuntimeError, match="sk-"), agentrec.session(path, mode="once"):
        raise RuntimeError(f"failed with {fake}")
    metadata, interactions = CassetteStore(path).load()
    assert metadata.error is not None
    assert fake not in metadata.error.message
    assert not privacy_findings(interactions, metadata)
    assert fake not in (path / "cassette.json").read_text()
