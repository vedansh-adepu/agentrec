"""Optional legacy httpx transport remains offline on replay."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

import agentrec


def test_legacy_httpx_sync_transport(tmp_path: Path) -> None:
    path = tmp_path / "legacy"
    calls = 0

    def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"call": calls})

    with (
        agentrec.session(path, mode="once") as rec,
        httpx.Client(
            transport=agentrec.legacy_httpx_transport(
                rec, httpx.MockTransport(upstream)
            )
        ) as client,
    ):
        assert client.get("https://example.test/").json() == {"call": 1}
    with (
        agentrec.session(path, mode="none") as rec,
        httpx.Client(
            transport=agentrec.legacy_httpx_transport(
                rec, httpx.MockTransport(upstream)
            )
        ) as client,
    ):
        assert client.get("https://example.test/").json() == {"call": 1}
    assert calls == 1


def test_legacy_httpx_async_transport(tmp_path: Path) -> None:
    path = tmp_path / "legacy-async"
    calls = 0

    async def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"call": calls})

    async def run(mode: str) -> dict[str, int]:
        async with (
            agentrec.session(path, mode=mode) as rec,
            httpx.AsyncClient(
                transport=agentrec.legacy_async_httpx_transport(
                    rec, httpx.MockTransport(upstream)
                )
            ) as client,
        ):
            return (await client.get("https://example.test/")).json()

    assert asyncio.run(run("once")) == {"call": 1}
    assert asyncio.run(run("none")) == {"call": 1}
    assert calls == 1
