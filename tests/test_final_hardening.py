"""Lifecycle, streaming, and async error regressions from final review."""

import asyncio
import importlib
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

import agentrec
from agentrec.cassette.store import CassetteLockedError, CassetteStore


def test_recording_session_holds_writer_lease_until_close(tmp_path: Path) -> None:
    path = tmp_path / "run"
    first = agentrec.session(path, mode="once")
    try:
        for mode in ("once", "all", "new_episodes"):
            with pytest.raises(CassetteLockedError):
                agentrec.session(path, mode=mode)
    finally:
        first.close()
    with agentrec.session(path, mode="all"):
        pass
    assert not (tmp_path / ".run.agentrec.lock").exists()


def test_failed_finalize_releases_writer_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = agentrec.session(tmp_path / "run", mode="once")

    def failure(*args, **kwargs):
        raise OSError("disk failure")

    monkeypatch.setattr(rec.store, "save", failure)
    with pytest.raises(OSError, match="disk failure"):
        rec.close()
    assert not (tmp_path / ".run.agentrec.lock").exists()


def test_closed_session_rejects_tool_calls_before_executing(tmp_path: Path) -> None:
    rec = agentrec.session(tmp_path / "run", mode="once")

    @rec.tool
    def forbidden() -> int:
        raise AssertionError("executed closed tool")

    rec.close()
    with pytest.raises(RuntimeError, match="closed"):
        forbidden()


@pytest.mark.parametrize("library", ["httpx2", "httpx"])
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_progressive_sse_close_and_midstream_timeout(
    tmp_path: Path, library: str, asynchronous: bool, fail: bool
) -> None:
    lib = importlib.import_module(library)
    path = tmp_path / "stream"
    produced = []
    calls = 0

    class SyncStream(lib.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            produced.append(1)
            yield b"data: one\n\n"
            if fail:
                raise lib.ReadTimeout("stream interrupted")
            produced.append(2)
            yield b"data: two\n\n"

        def close(self):
            pass

    class AsyncStream(lib.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            for chunk in SyncStream():
                yield chunk

        async def aclose(self):
            pass

    def upstream(request):
        nonlocal calls
        calls += 1
        return lib.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=AsyncStream() if asynchronous else SyncStream(),
        )

    def sync_run(mode):
        with agentrec.session(path, mode=mode, allow_failed=True) as rec:
            transport = (
                rec.transport(lib.MockTransport(upstream))
                if library == "httpx2"
                else agentrec.legacy_httpx_transport(rec, lib.MockTransport(upstream))
            )
            with lib.Client(transport=transport) as client:
                if fail:
                    with pytest.raises(lib.ReadTimeout, match="stream interrupted"):
                        client.get("https://example.test/stream")
                else:
                    with client.stream(
                        "GET", "https://example.test/stream"
                    ) as response:
                        iterator = response.iter_bytes()
                        assert (
                            next(iterator) == b"data: one\n\n"
                            if mode == "once"
                            else response.read() == b"data: one\n\ndata: two\n\n"
                        )
                        if mode == "once":
                            assert produced == [1]

    async def async_run(mode):
        async with agentrec.session(path, mode=mode, allow_failed=True) as rec:
            transport = (
                rec.async_transport(lib.MockTransport(upstream))
                if library == "httpx2"
                else agentrec.legacy_async_httpx_transport(
                    rec, lib.MockTransport(upstream)
                )
            )
            async with lib.AsyncClient(transport=transport) as client:
                if fail:
                    with pytest.raises(lib.ReadTimeout, match="stream interrupted"):
                        await client.get("https://example.test/stream")
                else:
                    async with client.stream(
                        "GET", "https://example.test/stream"
                    ) as response:
                        if mode == "once":
                            iterator = response.aiter_bytes()
                            assert await anext(iterator) == b"data: one\n\n"
                            assert produced == [1]
                        else:
                            assert (
                                await response.aread() == b"data: one\n\ndata: two\n\n"
                            )

    for mode in ("once", "none"):
        if asynchronous:
            asyncio.run(async_run(mode))
        else:
            sync_run(mode)
    assert calls == 1
    _, items = CassetteStore(path).load()
    assert len(items) == 1
    if fail:
        assert items[0].error.type == "ReadTimeout"
    else:
        assert produced == [1, 2]
        assert items[0].response["body"] == "data: one\n\ndata: two\n\n"


def test_async_tool_error_and_secret_redaction(tmp_path: Path) -> None:
    path = tmp_path / "async-error"

    async def run(mode):
        async with agentrec.session(path, mode=mode) as rec:

            @rec.tool
            async def broken(value: int) -> int:
                if mode == "none":
                    raise AssertionError("executed replay tool")
                raise ValueError("bad sk-FAKEFAKEFAKEFAKE")

            error = ValueError if mode == "once" else agentrec.ReplayedToolError
            with pytest.raises(error):
                await broken(1)

    asyncio.run(run("once"))
    asyncio.run(run("none"))
    _, items = CassetteStore(path).load()
    assert "sk-FAKE" not in items[0].error.message


@pytest.mark.parametrize("library", ["httpx2", "httpx"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_default_upstream_is_lazy_reused_and_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, library: str, asynchronous: bool
) -> None:
    lib = importlib.import_module(library)
    path = tmp_path / "default"
    created = closed = calls = 0

    class SyncUpstream(lib.BaseTransport):
        def handle_request(self, request):
            nonlocal calls
            calls += 1
            return lib.Response(200, content=str(calls).encode())

        def close(self):
            nonlocal closed
            closed += 1

    class AsyncUpstream(lib.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return SyncUpstream().handle_request(request)

        async def aclose(self):
            nonlocal closed
            closed += 1

    def factory():
        nonlocal created
        created += 1
        return AsyncUpstream() if asynchronous else SyncUpstream()

    monkeypatch.setattr(
        lib, "AsyncHTTPTransport" if asynchronous else "HTTPTransport", factory
    )

    async def async_run(mode):
        async with agentrec.session(path, mode=mode) as rec:
            transport = (
                rec.async_transport()
                if library == "httpx2"
                else agentrec.legacy_async_httpx_transport(rec)
            )
            async with lib.AsyncClient(transport=transport) as client:
                assert (await client.get("https://example.test")).content == b"1"
                assert (await client.get("https://example.test")).content == b"2"

    def sync_run(mode):
        with agentrec.session(path, mode=mode) as rec:
            transport = (
                rec.transport()
                if library == "httpx2"
                else agentrec.legacy_httpx_transport(rec)
            )
            with lib.Client(transport=transport) as client:
                assert client.get("https://example.test").content == b"1"
                assert client.get("https://example.test").content == b"2"

    for mode in ("once", "none"):
        asyncio.run(async_run(mode)) if asynchronous else sync_run(mode)
    assert created == 1 and closed == 1 and calls == 2
