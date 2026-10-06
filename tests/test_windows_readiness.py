"""Portable storage regressions and fake-only Windows IPC checks."""

import hashlib
import socket
import subprocess
from pathlib import Path

import pytest
import pytest_socket

from agentrec.cassette.store import (
    CassetteLockedError,
    CassetteStore,
    CassetteStoreError,
    _atomic_write,
)


@pytest.mark.parametrize("failure", [PermissionError, KeyboardInterrupt])
def test_replace_failure_preserves_target_and_cleans_temporary(
    tmp_path, monkeypatch, failure
):
    import agentrec.cassette.store as module

    target = tmp_path / "file"
    target.write_bytes(b"original")
    attempts = []

    def fail(*args):
        attempts.append(args)
        raise failure()

    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(failure):
        _atomic_write(target, b"replacement")
    assert len(attempts) == (2 if failure is PermissionError else 1)
    assert target.read_bytes() == b"original"
    assert set(tmp_path.iterdir()) == {target}


def test_write_handle_is_closed_before_replace(tmp_path, monkeypatch):
    import agentrec.cassette.store as module

    streams = []
    fdopen, replace = module.os.fdopen, module.os.replace

    def observe_open(*args, **kwargs):
        stream = fdopen(*args, **kwargs)
        streams.append(stream)
        return stream

    def observe_replace(*args):
        assert streams and all(stream.closed for stream in streams)
        replace(*args)

    monkeypatch.setattr(module.os, "fdopen", observe_open)
    monkeypatch.setattr(module.os, "replace", observe_replace)
    _atomic_write(tmp_path / "file", b"complete")
    assert (tmp_path / "file").read_bytes() == b"complete"


def test_interruption_releases_writer_lock(tmp_path):
    store = CassetteStore(tmp_path / "run")
    with pytest.raises(KeyboardInterrupt), store.writer_lock():
        raise KeyboardInterrupt()
    assert not (tmp_path / ".run.agentrec.lock").exists()
    with store.writer_lock():
        pass


def test_case_alias_cannot_acquire_second_lock(tmp_path):
    probe = tmp_path / "CaseProbe"
    probe.write_bytes(b"probe")
    if not (tmp_path / "caseprobe").exists():
        pytest.skip("filesystem is case sensitive; alias locking needs insensitive FS")
    with (
        CassetteStore(tmp_path / "Run").writer_lock(),
        pytest.raises(CassetteLockedError),
        CassetteStore(tmp_path / "run").writer_lock(),
    ):
        pass


@pytest.mark.parametrize(
    "value", [r"C:\outside", r"..\outside", r"\\host\share", "a" * 64 + "\\x"]
)
def test_windows_path_spellings_cannot_be_keys_or_members(tmp_path, value):
    store = CassetteStore(tmp_path / "run")
    with pytest.raises(CassetteStoreError):
        store.path_for_key(value)
    with pytest.raises(CassetteStoreError):
        store._file(value)
    assert not list(tmp_path.iterdir())


def test_golden_bytes_and_checkout_attributes_are_lf():
    import json

    root = Path(__file__).resolve().parents[1]
    golden = root / "tests/data/golden-v2"
    payload = (golden / "interactions.jsonl").read_bytes()
    metadata = json.loads((golden / "cassette.json").read_bytes())
    assert b"\r\n" not in payload
    assert hashlib.sha256(payload).hexdigest() == metadata["content_sha256"]
    paths = [
        "tests/data/golden-v2/interactions.jsonl",
        "tests/data/golden-v2/cassette.json",
        "docs/ci.md",
    ]
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", *paths],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == [f"{path}: eol: lf" for path in paths]


def test_windows_ipc_uses_only_fixed_loopback_and_keeps_network_guard(monkeypatch):
    import conftest

    created = []

    class FakeSocket:
        def __init__(self, *args, **kwargs):
            self.closed = False
            self.fileno = kwargs.get("fileno")
            created.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def bind(self, address):
            assert address == ("127.0.0.1", 0)

        def listen(self, backlog):
            assert backlog == 1

        def getsockname(self):
            return ("127.0.0.1", 12345)

        def connect(self, address):
            assert address == ("127.0.0.1", 12345)

        def _accept(self):
            return 42, ("127.0.0.1", 12346)

        def close(self):
            self.closed = True

    monkeypatch.setattr(conftest, "_REAL_SOCKET", FakeSocket)
    guarded = socket.socket
    server, client = conftest._loopback_socketpair()
    assert created[0].closed and not client.closed and server.fileno == 42
    assert socket.socket is guarded
    with pytest.raises(pytest_socket.SocketBlockedError):
        socket.socket(socket.AF_INET)
    for kwargs in (
        {"family": socket.AF_UNIX} if hasattr(socket, "AF_UNIX") else {"family": -1},
        {"type": socket.SOCK_DGRAM},
        {"proto": 1},
    ):
        with pytest.raises(ValueError):
            conftest._loopback_socketpair(**kwargs)


def test_collected_test_ids_fit_windows_environment_limit(request):
    # pytest exports each node ID through PYTEST_CURRENT_TEST. Preserve hostile
    # input sizes but prevent payload-generated IDs exceeding Windows' limit.
    for item in request.session.items:
        assert len((item.nodeid + " (teardown)").encode("utf-16-le")) // 2 < 32767
