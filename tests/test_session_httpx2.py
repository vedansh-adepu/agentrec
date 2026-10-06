"""Offline session integration with official SDKs and fake HTTP upstreams."""

from __future__ import annotations

import asyncio
from pathlib import Path

import anthropic
import httpx2
import openai
import pytest

import agentrec
from agentrec.errors import ReplayedToolError, ReplayMissError


def chat_response(text: str) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": "fake-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
    }


def test_openai_identical_http_requests_replay_distinct_responses(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run"
    calls: list[httpx2.Request] = []

    def upstream(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(200, json=chat_response(str(len(calls))))

    def invoke(rec: agentrec.Session) -> list[str | None]:
        client = openai.OpenAI(
            api_key="test",
            base_url="https://example.test/v1",
            max_retries=0,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            return [
                client.chat.completions.create(
                    model="fake-model", messages=[{"role": "user", "content": "same"}]
                )
                .choices[0]
                .message.content
                for _ in range(3)
            ]
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == ["1", "2", "3"]
    assert len(calls) == 3
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == ["1", "2", "3"]
        assert rec.play_count == 3
    assert len(calls) == 3


def test_anthropic_offline_nonstreaming_replay(tmp_path: Path) -> None:
    path = tmp_path / "run"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-test",
                "content": [{"type": "text", "text": "fixed"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    def invoke(rec: agentrec.Session) -> str:
        client = anthropic.Anthropic(
            api_key="test",
            base_url="https://example.test",
            max_retries=0,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            result = client.messages.create(
                model="claude-test",
                max_tokens=10,
                messages=[{"role": "user", "content": "hello"}],
            )
            return result.content[0].text
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == "fixed"
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == "fixed"
    assert calls == 1


def test_tool_mutation_and_exception_are_replayed_without_execution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run"
    executions = 0

    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def mutate(value: dict[str, int]) -> dict[str, int]:
            nonlocal executions
            executions += 1
            value["x"] = 9
            return value

        @rec.tool
        def fail(value: int) -> None:
            nonlocal executions
            executions += 1
            raise RuntimeError(f"bad {value}")

        argument = {"x": 1}
        assert mutate(argument) == {"x": 9}
        assert argument == {"x": 9}
        with pytest.raises(RuntimeError, match="bad 2"):
            fail(2)

    with agentrec.session(path, mode="none") as rec:

        @rec.tool
        def mutate(value: dict[str, int]) -> dict[str, int]:
            raise AssertionError("executed")

        @rec.tool
        def fail(value: int) -> None:
            raise AssertionError("executed")

        assert mutate({"x": 1}) == {"x": 9}
        with pytest.raises(ReplayedToolError, match="RuntimeError: bad 2"):
            fail(2)
    assert executions == 2


def test_replay_miss_never_calls_upstream(tmp_path: Path) -> None:
    path = tmp_path / "run"
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
        client.get("https://example.test/one")
    with (
        agentrec.session(path, mode="none", fail_on_unplayed=False) as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
        pytest.raises(ReplayMissError),
    ):
        client.get("https://example.test/two")
    assert calls == 1


def test_async_tool_and_transport_replay(tmp_path: Path) -> None:
    path = tmp_path / "run"
    calls = 0

    async def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json={"value": calls})

    async def run(mode: str) -> tuple[dict[str, int], int]:
        async with agentrec.session(path, mode=mode) as rec:

            @rec.tool
            async def lookup(value: int) -> int:
                if mode == "none":
                    raise AssertionError("tool executed")
                return value + 1

            async with httpx2.AsyncClient(
                transport=rec.async_transport(httpx2.MockTransport(upstream))
            ) as client:
                response = await client.get("https://example.test/async")
                result = await lookup(2)
                return response.json(), result

    assert asyncio.run(run("once")) == ({"value": 1}, 3)
    assert asyncio.run(run("none")) == ({"value": 1}, 3)
    assert calls == 1


def test_failed_recording_has_failed_status(tmp_path: Path) -> None:
    path = tmp_path / "failed"
    with (
        pytest.raises(ValueError, match="agent failed"),
        agentrec.session(path, mode="once"),
    ):
        raise ValueError("agent failed")
    with pytest.raises(Exception, match="allow_failed"):
        agentrec.session(path, mode="none")
    with agentrec.session(path, mode="none", allow_failed=True):
        pass


def test_openai_sse_stream_replays_identical_parsed_events(tmp_path: Path) -> None:
    import json

    path = tmp_path / "stream"
    calls = 0
    chunks = [
        {
            "id": "chatcmpl-stream",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "fake-model",
            "choices": [
                {"index": 0, "delta": {"content": text}, "finish_reason": None}
            ],
        }
        for text in ("A", "B")
    ]
    body = (
        b"".join(b"data: " + json.dumps(chunk).encode() + b"\n\n" for chunk in chunks)
        + b"data: [DONE]\n\n"
    )

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=body
        )

    def invoke(rec: agentrec.Session) -> list[str | None]:
        client = openai.OpenAI(
            api_key="test",
            base_url="https://example.test/v1",
            max_retries=0,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            stream = client.chat.completions.create(
                model="fake-model",
                messages=[{"role": "user", "content": "stream"}],
                stream=True,
            )
            return [event.choices[0].delta.content for event in stream]
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == ["A", "B"]
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == ["A", "B"]
    assert calls == 1


def test_anthropic_sse_stream_replays_identical_event_types(tmp_path: Path) -> None:
    import json

    path = tmp_path / "stream"
    calls = 0
    events = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": "claude-test",
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 0},
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hello"},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    body = b"".join(
        b"event: "
        + name.encode()
        + b"\n"
        + b"data: "
        + json.dumps(data).encode()
        + b"\n\n"
        for name, data in events
    )

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=body
        )

    def invoke(rec: agentrec.Session) -> list[str]:
        client = anthropic.Anthropic(
            api_key="test",
            base_url="https://example.test",
            max_retries=0,
            http_client=httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            ),
        )
        try:
            stream = client.messages.create(
                model="claude-test",
                max_tokens=10,
                messages=[{"role": "user", "content": "stream"}],
                stream=True,
            )
            return [event.type for event in stream]
        finally:
            client.close()

    with agentrec.session(path, mode="once") as rec:
        assert invoke(rec) == [name for name, _ in events]
    with agentrec.session(path, mode="none") as rec:
        assert invoke(rec) == [name for name, _ in events]
    assert calls == 1


def test_record_modes_once_new_episodes_and_all(tmp_path: Path) -> None:
    path = tmp_path / "modes"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json={"call": calls})

    def call(rec: agentrec.Session, suffix: str) -> dict[str, int]:
        with httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client:
            return client.get(f"https://example.test/{suffix}").json()

    with agentrec.session(path, mode="once") as rec:
        assert call(rec, "one") == {"call": 1}
    with agentrec.session(path, mode="once") as rec:
        assert call(rec, "one") == {"call": 1}
        with pytest.raises(ReplayMissError):
            call(rec, "two")
    with agentrec.session(path, mode="new_episodes") as rec:
        assert call(rec, "one") == {"call": 1}
        assert call(rec, "two") == {"call": 2}
    with agentrec.session(path, mode="none") as rec:
        assert call(rec, "one") == {"call": 1}
        assert call(rec, "two") == {"call": 2}
    with agentrec.session(path, mode="all") as rec:
        assert call(rec, "one") == {"call": 3}
    with agentrec.session(path, mode="none") as rec:
        assert call(rec, "one") == {"call": 3}
    assert calls == 3


def test_transport_exception_replays_as_same_httpx2_type(tmp_path: Path) -> None:
    path = tmp_path / "timeout"
    calls = 0

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise httpx2.ConnectTimeout("delayed", request=request)

    with (
        pytest.raises(httpx2.ConnectTimeout),
        agentrec.session(path, mode="once") as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        client.get("https://example.test/timeout")
    with (
        pytest.raises(httpx2.ConnectTimeout),
        agentrec.session(path, mode="none", allow_failed=True) as rec,
        httpx2.Client(
            transport=rec.transport(httpx2.MockTransport(upstream))
        ) as client,
    ):
        client.get("https://example.test/timeout")
    assert calls == 1


def test_official_async_clients_replay_offline(tmp_path: Path) -> None:
    openai_path = tmp_path / "openai"
    anthropic_path = tmp_path / "anthropic"
    calls = 0

    async def openai_upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json=chat_response("async"))

    async def anthropic_upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200,
            json={
                "id": "msg_async",
                "type": "message",
                "role": "assistant",
                "model": "claude-test",
                "content": [{"type": "text", "text": "async"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    async def invoke_openai(mode: str) -> str | None:
        async with agentrec.session(openai_path, mode=mode) as rec:
            client = openai.AsyncOpenAI(
                api_key="test",
                base_url="https://example.test/v1",
                max_retries=0,
                http_client=httpx2.AsyncClient(
                    transport=rec.async_transport(httpx2.MockTransport(openai_upstream))
                ),
            )
            try:
                result = await client.chat.completions.create(
                    model="fake-model",
                    messages=[{"role": "user", "content": "same"}],
                )
                return result.choices[0].message.content
            finally:
                await client.close()

    async def invoke_anthropic(mode: str) -> str:
        async with agentrec.session(anthropic_path, mode=mode) as rec:
            client = anthropic.AsyncAnthropic(
                api_key="test",
                base_url="https://example.test",
                max_retries=0,
                http_client=httpx2.AsyncClient(
                    transport=rec.async_transport(
                        httpx2.MockTransport(anthropic_upstream)
                    )
                ),
            )
            try:
                result = await client.messages.create(
                    model="claude-test",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "same"}],
                )
                return result.content[0].text
            finally:
                await client.close()

    assert asyncio.run(invoke_openai("once")) == "async"
    assert asyncio.run(invoke_openai("none")) == "async"
    assert asyncio.run(invoke_anthropic("once")) == "async"
    assert asyncio.run(invoke_anthropic("none")) == "async"
    assert calls == 2


def test_async_tool_calls_record_safely_under_gather(tmp_path: Path) -> None:
    path = tmp_path / "concurrent"

    async def record() -> None:
        async with agentrec.session(path, mode="once") as rec:

            @rec.tool
            async def work(value: int) -> int:
                await asyncio.sleep(0)
                return value * 2

            assert await asyncio.gather(*(work(n) for n in range(10))) == [
                n * 2 for n in range(10)
            ]

    asyncio.run(record())
    with agentrec.session(path, mode="none") as rec:

        @rec.tool
        def work(value: int) -> int:
            raise AssertionError("executed")

        assert [work(n) for n in range(10)] == [n * 2 for n in range(10)]


def test_threaded_tool_recording_has_contiguous_sequence(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "threads"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def calculate(value: int) -> int:
            return value * 3

        with ThreadPoolExecutor(max_workers=4) as pool:
            assert sorted(pool.map(calculate, range(20))) == [n * 3 for n in range(20)]
    from agentrec.cassette.store import CassetteStore

    _, interactions = CassetteStore(path).load()
    assert [entry.seq for entry in interactions] == list(range(20))
    assert {entry.request["arguments"]["value"] for entry in interactions} == set(
        range(20)
    )


def test_nonfinite_tool_result_round_trips_through_cassette(tmp_path: Path) -> None:
    import math

    from agentrec.cassette.store import CassetteStore
    from agentrec.validation import validate_v2_cassette

    path = tmp_path / "nonfinite"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def measure(value: float) -> dict[str, float]:
            return {
                "positive": float("inf"),
                "negative": float("-inf"),
                "missing": float("nan"),
                "input": value,
            }

        original = measure(float("inf"))
        assert math.isnan(original["missing"])
    assert validate_v2_cassette(path, level="integrity")["ok"]
    disk = (path / "interactions.jsonl").read_text(encoding="utf-8")
    assert '"$float":"inf"' in disk
    assert '"$float":"-inf"' in disk
    assert '"$float":"nan"' in disk
    _, interactions = CassetteStore(path).load()
    assert not interactions[0].key_inputs_redacted
    with agentrec.session(path, mode="none") as rec:

        @rec.tool
        def measure(value: float) -> dict[str, float]:
            raise AssertionError("tool executed")

        replayed = measure(float("inf"))
    assert replayed["positive"] == float("inf")
    assert replayed["negative"] == float("-inf")
    assert math.isnan(replayed["missing"])
    assert replayed["input"] == float("inf")
