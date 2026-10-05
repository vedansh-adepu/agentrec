"""Schema-v2 storage regressions for ownership, safety, and atomic writes."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentrec.cassette.model import CassetteMetadata, Interaction, PolicyRecord
from agentrec.cassette.store import (
    CassetteLockedError,
    CassetteOwnershipError,
    CassetteStore,
    CassetteStoreError,
    CassetteVersionError,
)


def sample_interaction() -> Interaction:
    return Interaction(
        seq=0,
        kind="tool",
        key="a" * 64,
        occurrence=0,
        key_inputs_redacted=False,
        request={"name": "lookup", "arguments": {"id": 1}},
        response={"result": "ok"},
        started_at=datetime.now(UTC),
        duration_ms=1.25,
    )


def sample_metadata(interactions: list[Interaction]) -> CassetteMetadata:
    data = b"".join(
        json.dumps(
            item.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        + b"\n"
        for item in interactions
    )
    now = datetime.now(UTC)
    return CassetteMetadata(
        agentrec_version="1.0.0rc1",
        match_policy=PolicyRecord(name="agentrec-default", version=1, config={}),
        redaction_policy_version=1,
        status="complete",
        created_at=now,
        finalized_at=now,
        interaction_count=len(interactions),
        content_sha256=hashlib.sha256(data).hexdigest(),
    )


def test_schema_v2_round_trips_and_writes_only_two_files(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "run")
    interactions = [sample_interaction()]
    metadata = sample_metadata(interactions)
    store.save(metadata, interactions)
    loaded_metadata, loaded = store.load()
    assert loaded_metadata == metadata
    assert loaded == interactions
    assert store.owns()
    assert {item.name for item in store.path.iterdir()} == {
        "cassette.json",
        "interactions.jsonl",
    }


def test_existing_cassette_requires_explicit_replacement(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "run")
    interactions = [sample_interaction()]
    metadata = sample_metadata(interactions)
    store.save(metadata, interactions)
    before = (store.path / "cassette.json").read_bytes()
    with pytest.raises(CassetteOwnershipError, match="already exists"):
        store.save(metadata, interactions)
    assert (store.path / "cassette.json").read_bytes() == before
    store.save(metadata, interactions, replace=True)


def test_unowned_directory_is_never_replaced_or_deleted(tmp_path: Path) -> None:
    target = tmp_path / "notes"
    target.mkdir()
    important = target / "important.txt"
    important.write_text("keep")
    store = CassetteStore(target)
    with pytest.raises(CassetteOwnershipError):
        store.save(sample_metadata([]), [], replace=True)
    assert important.read_text() == "keep"


def test_public_key_path_rejects_traversal(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "run")
    for key in ("../escape", "A" * 64, "a" * 63, "a" * 64 + "/x"):
        with pytest.raises(CassetteStoreError, match="SHA-256"):
            store.path_for_key(key)
    assert store.path_for_key("a" * 64).parent == store.path


def test_symlinked_cassette_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(CassetteStoreError, match="symlink"):
        CassetteStore(link)


def test_second_writer_is_rejected(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "run")
    with store.writer_lock(), pytest.raises(CassetteLockedError), store.writer_lock():
        pass
    assert not (tmp_path / ".run.agentrec.lock").exists()


def test_v1_cassette_has_clear_migration_error(tmp_path: Path) -> None:
    run = tmp_path / "v1"
    run.mkdir()
    (run / "metadata.json").write_text('{"schema_version":1}')
    with pytest.raises(CassetteVersionError, match="re-record"):
        CassetteStore(run).load()


def test_invalid_metadata_and_interaction_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Interaction.model_validate({**sample_interaction().model_dump(), "ignored": 1})
    with pytest.raises(ValidationError):
        Interaction.model_validate(
            {
                **sample_interaction().model_dump(),
                "response": None,
                "error": None,
            }
        )


def test_failed_atomic_replace_leaves_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentrec.cassette.store as module

    store = CassetteStore(tmp_path / "run")
    interaction = sample_interaction()
    metadata = sample_metadata([interaction])

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk failure"):
        store.save(metadata, [interaction])
    assert list(store.path.glob("*.tmp")) == []
    assert not (store.path / "cassette.json").exists()


def test_atomic_replace_retries_permission_error_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentrec.cassette.store as module

    original = module.os.replace
    attempts = 0

    def transient(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("Windows sharing violation")
        original(source, destination)

    monkeypatch.setattr(module.os, "replace", transient)
    target = tmp_path / "atomic"
    module._atomic_write(target, b"complete")
    assert attempts == 2 and target.read_bytes() == b"complete"
    assert not list(tmp_path.glob("*.tmp"))


def test_windows_skips_directory_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentrec.cassette.store as module

    original_fsync = module.os.fsync
    calls = 0

    def observed(fd: int) -> None:
        nonlocal calls
        calls += 1
        original_fsync(fd)

    # Replace the module's os reference, not the process-wide os.name.
    from types import SimpleNamespace

    monkeypatch.setattr(
        module,
        "os",
        SimpleNamespace(
            name="nt",
            fdopen=module.os.fdopen,
            fsync=observed,
            replace=module.os.replace,
        ),
    )
    target = tmp_path / "atomic"
    module._atomic_write(target, b"complete")
    assert calls == 1 and target.read_bytes() == b"complete"
