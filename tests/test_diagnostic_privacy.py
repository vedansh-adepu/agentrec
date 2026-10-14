"""Synthetic credential-shaped inputs never escape through diagnostics."""

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from typer.testing import CliRunner

from agentrec.cassette.replay import ReplayIndex
from agentrec.cassette.store import CassetteStore, CassetteVersionError
from agentrec.cli import app
from agentrec.errors import ReplayMissError
from agentrec.redaction import Redactor
from agentrec.validation import validate_v2_cassette

GOLDEN = Path(__file__).parent / "data/golden-v2"
SYNTHETIC = [
    "sk-" + "FAKE" * 8,
    "sk-proj-" + "FAKE" * 8,
    "sk-proj-FAK" + "*" * 20 + "WXYZ",
    "sk-ant-" + "FAKE" * 8,
]


@pytest.mark.parametrize("secret", SYNTHETIC)
@pytest.mark.parametrize("encoded", [False, True])
def test_replay_and_inspect_miss_redact_all_request_fields(
    tmp_path: Path, secret: str, encoded: bool
) -> None:
    value = quote(secret, safe="") if encoded else secret
    request = {
        "kind": "http",
        "method": "POST",
        "url": "https://example.test/run?api_key=" + value,
        "headers": {"authorization": secret, "content-type": "application/json"},
        "body": json.dumps({secret: secret}),
    }
    with pytest.raises(ReplayMissError) as caught:
        ReplayIndex([]).play("f" * 64, request)
    messages = [str(caught.value), repr(caught.value)]
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request), encoding="utf-8")
    for flags in ([], ["--debug"]):
        result = CliRunner().invoke(
            app, [*flags, "inspect-miss", str(GOLDEN), str(source)]
        )
        assert result.exit_code == 1
        messages.extend([result.output, str(result.exception), repr(result.exception)])
    assert all(secret not in message and value not in message for message in messages)
    assert "REDACTED" in str(caught.value)


def test_replay_diagnostics_use_configured_redactor() -> None:
    request = {"method": "GET", "url": "https://example.test/CUSTOM-PRIVATE"}
    redactor = Redactor(custom_patterns={"custom": "CUSTOM-PRIVATE"})
    with pytest.raises(ReplayMissError) as caught:
        ReplayIndex([], redactor=redactor).play("f" * 64, request)
    assert "CUSTOM-PRIVATE" not in str(caught.value)


@pytest.mark.parametrize("secret", SYNTHETIC)
@pytest.mark.parametrize("container", [False, True])
def test_unknown_schema_reports_type_without_value(
    tmp_path: Path, secret: str, container: bool
) -> None:
    value = [secret] if container else secret
    (tmp_path / "cassette.json").write_text(
        json.dumps({"schema_version": value}), encoding="utf-8"
    )
    with pytest.raises(CassetteVersionError) as caught:
        CassetteStore(tmp_path).load()
    messages = [str(caught.value), repr(caught.value)]
    validation = validate_v2_cassette(tmp_path)
    messages.append(json.dumps(validation))
    for flags in ([], ["--json"]):
        result = CliRunner().invoke(app, ["validate", str(tmp_path), *flags])
        assert result.exit_code == 1
        messages.append(result.output)
    assert all(secret not in message for message in messages)
    assert "unsupported" in str(caught.value)
    assert ("type list" if container else "type str") in str(caught.value)


@pytest.mark.parametrize("secret", SYNTHETIC)
def test_validation_errors_redact_invalid_record_values(
    tmp_path: Path, secret: str
) -> None:
    metadata, interactions = CassetteStore(GOLDEN).load()
    record = interactions[0].model_dump(mode="json")
    record["duration_ms"] = secret
    (tmp_path / "cassette.json").write_text(
        metadata.model_dump_json(), encoding="utf-8"
    )
    (tmp_path / "interactions.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )
    for flags in ([], ["--json"]):
        result = CliRunner().invoke(app, ["validate", str(tmp_path), *flags])
        assert result.exit_code == 1
        assert secret not in result.output
    assert secret not in json.dumps(validate_v2_cassette(tmp_path))
