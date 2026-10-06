"""Hostile input must fail as a documented error without filesystem writes."""

import json
from contextlib import suppress
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_cassette_v2_store import sample_interaction, sample_metadata
from test_properties import values

from agentrec.cassette.store import CassetteStore
from agentrec.errors import AgentRecError


@settings(
    max_examples=150,
    deadline=None,
    database=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(values, st.booleans())
def test_random_cassette_json_is_read_only_or_documented_error(
    tmp_path: Path, value, mutate_metadata: bool
):
    target = tmp_path / "fuzz"
    target.mkdir(exist_ok=True)
    metadata = sample_metadata([sample_interaction()]).model_dump(mode="json")
    interaction = sample_interaction().model_dump(mode="json")
    (target / "cassette.json").write_text(
        json.dumps(value if mutate_metadata else metadata), encoding="utf-8"
    )
    (target / "interactions.jsonl").write_text(
        json.dumps(interaction if mutate_metadata else value) + "\n", encoding="utf-8"
    )
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    with suppress(AgentRecError):
        CassetteStore(target).load()
    after = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    "payload",
    [
        b"[" * 20000 + b"0" + b"]" * 20000,
        b'{"schema_version":' + b"9" * 5000 + b"}",
        b"\xff",
        b"null",
    ],
)
def test_deep_huge_and_invalid_encoded_metadata_is_documented_error(
    tmp_path: Path, payload: bytes
):
    (tmp_path / "cassette.json").write_bytes(payload)
    with pytest.raises(AgentRecError):
        CassetteStore(tmp_path).load()


@pytest.mark.parametrize(
    "key", ["../../outside", "/tmp/escape", "C:\\escape", "0" * 10000]
)
def test_hostile_interaction_keys_never_escape(tmp_path: Path, key: str):
    metadata = sample_metadata([sample_interaction()]).model_dump(mode="json")
    item = sample_interaction().model_dump(mode="json")
    item["key"] = key
    (tmp_path / "cassette.json").write_text(
        json.dumps(metadata), encoding="utf-8", newline="\n"
    )
    (tmp_path / "interactions.jsonl").write_text(
        json.dumps(item), encoding="utf-8", newline="\n"
    )
    with pytest.raises(AgentRecError):
        CassetteStore(tmp_path).load()
