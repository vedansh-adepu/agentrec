"""Unsafe paths, invalid metadata, and interrupted finalize must fail closed."""

import builtins
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_cassette_v2_store import sample_interaction, sample_metadata

import agentrec
from agentrec.cassette.model import CassetteMetadata
from agentrec.cassette.store import CassetteStore, CassetteStoreError, _atomic_write
from agentrec.validation import validate_v2_cassette


@pytest.mark.parametrize(
    "change",
    [{"schema_version": 1}, {"interaction_count": 2}, {"content_sha256": "0" * 64}],
)
def test_invalid_save_metadata_does_not_create_cassette(tmp_path: Path, change) -> None:
    item = sample_interaction()
    metadata = sample_metadata([item]).model_copy(update=change)
    with pytest.raises(CassetteStoreError):
        CassetteStore(tmp_path / "run").save(metadata, [item])
    assert not (tmp_path / "run").exists()


def test_noncontiguous_save_is_refused(tmp_path: Path) -> None:
    item = sample_interaction().model_copy(update={"seq": 1})
    with pytest.raises(CassetteStoreError, match="contiguous"):
        CassetteStore(tmp_path / "run").save(sample_metadata([item]), [item])
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"status": "recording"},
        {"finalized_at": None},
        {"status": "failed", "error": None},
    ],
)
def test_metadata_states_cannot_lie_about_finalization(change) -> None:
    source = sample_metadata([]).model_dump()
    source.update(change)
    with pytest.raises(ValidationError):
        CassetteMetadata.model_validate(source)


def test_symlinked_member_and_unknown_filename_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "run"
    path.mkdir()
    outside = tmp_path / "important"
    outside.write_text("keep")
    try:
        (path / "cassette.json").symlink_to(outside)
    except OSError as exc:
        import sys

        if sys.platform == "win32":
            pytest.skip(f"Windows symlink capability unavailable: {exc}")
        raise
    store = CassetteStore(path)
    with pytest.raises(CassetteStoreError):
        store.load()
    with pytest.raises(CassetteStoreError):
        store._file("../important")
    assert outside.read_text() == "keep"


def test_directory_sync_is_best_effort_and_file_sync_is_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentrec.cassette.store as module

    original = module.os.fsync
    calls = 0

    def directory_failure(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("directory sync unsupported")
        original(fd)

    monkeypatch.setattr(module.os, "fsync", directory_failure)
    _atomic_write(tmp_path / "file", b"complete")
    assert (tmp_path / "file").read_bytes() == b"complete"

    def file_failure(fd):
        raise OSError("file sync failed")

    monkeypatch.setattr(module.os, "fsync", file_failure)
    with pytest.raises(OSError, match="file sync failed"):
        _atomic_write(tmp_path / "file", b"replace")
    assert (tmp_path / "file").read_bytes() == b"complete"
    assert not list(tmp_path.glob("*.tmp"))


def test_crash_between_files_is_detected_by_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import agentrec.cassette.store as module

    path = tmp_path / "run"
    with agentrec.session(path) as rec:

        @rec.tool
        def lookup() -> int:
            return 1

        lookup()
    original = module._atomic_write

    def interrupted(path, data):
        if path.name == "cassette.json":
            raise OSError("interrupted metadata write")
        original(path, data)

    monkeypatch.setattr(module, "_atomic_write", interrupted)
    with pytest.raises(OSError), agentrec.session(path, mode="all") as rec:

        @rec.tool
        def lookup() -> int:
            return 2

        lookup()
    assert not validate_v2_cassette(path, level="integrity")["ok"]
    assert not (tmp_path / ".run.agentrec.lock").exists()


@pytest.mark.parametrize("asynchronous", [False, True])
def test_optional_httpx_import_has_install_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asynchronous: bool
) -> None:
    original = builtins.__import__

    def without_legacy(name, *args, **kwargs):
        if name.endswith("httpx_transport"):
            raise ImportError("optional httpx unavailable")
        return original(name, *args, **kwargs)

    with agentrec.session(tmp_path / "run") as rec:
        monkeypatch.setattr(builtins, "__import__", without_legacy)
        with pytest.raises(ImportError, match=r"agentrec\[httpx\]"):
            (
                agentrec.legacy_async_httpx_transport
                if asynchronous
                else agentrec.legacy_httpx_transport
            )(rec)


def test_session_validates_the_same_snapshot_it_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "run"
    with agentrec.session(path) as rec:

        @rec.tool
        def lookup() -> int:
            return 1

        lookup()
    original = CassetteStore._load_snapshot
    reads = 0

    def changing_file(store):
        nonlocal reads
        reads += 1
        captured = original(store)
        # A concurrent replace after the read must not substitute different records
        # between integrity validation and replay of the captured snapshot.
        (path / "interactions.jsonl").write_text("invalid concurrent replacement\n")
        return captured

    monkeypatch.setattr(CassetteStore, "_load_snapshot", changing_file)
    with agentrec.session(path, mode="none") as rec:

        @rec.tool
        def lookup() -> int:
            raise AssertionError("executed")

        assert lookup() == 1
    assert reads == 1
