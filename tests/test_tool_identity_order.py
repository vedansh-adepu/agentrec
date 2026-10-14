"""Stable tool identities and insertion order through real offline SDK requests."""

import asyncio
import json
from pathlib import Path

import anthropic
import httpx2
import openai
import pytest

import agentrec
from agentrec.cassette.store import CassetteStore
from agentrec.redaction import scrub
from agentrec.validation import validate_v2_cassette


def first() -> str:
    return "first"


def second() -> str:
    return "second"


@pytest.mark.parametrize("reverse", [False, True])
def test_same_name_different_qualnames_fail_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reverse: bool
) -> None:
    monkeypatch.setattr(first, "__name__", "lookup")
    monkeypatch.setattr(second, "__name__", "lookup")
    functions = [second, first] if reverse else [first, second]
    with agentrec.session(tmp_path / "run", mode="once") as rec:
        rec.tool(functions[0])
        with pytest.raises(agentrec.ToolIdentityError, match="name="):
            rec.tool(functions[1])
        assert rec._new == []


def test_explicit_names_replay_in_reverse_without_tool_effects(tmp_path: Path) -> None:
    path = tmp_path / "named"
    with agentrec.session(path, mode="once") as rec:
        assert rec.tool(first, name="lookup.first")() == "first"
        assert rec.tool(second, name="lookup.second")() == "second"
    with agentrec.session(path, mode="none") as rec:
        assert rec.tool(second, name="lookup.second")() == "second"
        assert rec.tool(first, name="lookup.first")() == "first"
        assert rec.all_played


def test_lambda_requires_name_and_blank_names_are_rejected(tmp_path: Path) -> None:
    with agentrec.session(tmp_path / "run", mode="once") as rec:
        with pytest.raises(agentrec.ToolIdentityError, match="name="):
            rec.tool(lambda: 1)
        for name in ("", " "):
            with pytest.raises(agentrec.ToolIdentityError, match="nonempty"):
                rec.tool(first, name=name)
        assert rec.tool(lambda: 1, name="one")() == 1
        assert rec.tool(first)() == "first"
        assert rec.tool(first)() == "first"


def test_module_is_part_of_registration_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(second, "__name__", first.__name__)
    monkeypatch.setattr(second, "__qualname__", first.__qualname__)
    monkeypatch.setattr(second, "__module__", "other_module")
    with agentrec.session(tmp_path / "run", mode="once") as rec:
        rec.tool(first)
        with pytest.raises(agentrec.ToolIdentityError):
            rec.tool(second)


def test_async_named_decorator_uses_explicit_identity(tmp_path: Path) -> None:
    calls = 0
    for mode in ("once", "none"):
        with agentrec.session(tmp_path / "async", mode=mode) as rec:

            @rec.tool(name="async.lookup")
            async def lookup() -> str:
                nonlocal calls
                calls += 1
                return "ok"

            assert asyncio.run(lookup()) == "ok"
    assert calls == 1


def result() -> dict:
    return {"zeta": 1, "alpha": {"z": 2, "a": 3}, "list": [{"y": 4, "b": 5}]}


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_tool_result_json_matches_next_real_sdk_request(
    tmp_path: Path, provider: str
) -> None:
    calls = 0
    tool_calls = 0
    path = tmp_path / provider

    def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        body = json.loads(request.content)
        final = len(body["messages"]) > 1
        if final:
            content = body["messages"][-1]["content"]
            if provider == "anthropic":
                content = content[0]["content"]
            assert content == json.dumps(result())
        if provider == "openai":
            message = (
                {"role": "assistant", "content": "done"}
                if final
                else {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": "{}"},
                        }
                    ],
                }
            )
            return httpx2.Response(
                200,
                json={
                    "id": "chat-1",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "fake",
                    "choices": [
                        {
                            "index": 0,
                            "message": message,
                            "finish_reason": "stop" if final else "tool_calls",
                        }
                    ],
                },
            )
        content = (
            [{"type": "text", "text": "done"}]
            if final
            else [{"type": "tool_use", "id": "call-1", "name": "lookup", "input": {}}]
        )
        return httpx2.Response(
            200,
            json={
                "id": "msg-1",
                "type": "message",
                "role": "assistant",
                "model": "fake",
                "content": content,
                "stop_reason": "end_turn" if final else "tool_use",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    for mode in ("once", "none"):
        with agentrec.session(path, mode=mode) as rec:

            @rec.tool
            def lookup() -> dict:
                nonlocal tool_calls
                tool_calls += 1
                return result()

            http = httpx2.Client(
                transport=rec.transport(httpx2.MockTransport(upstream))
            )
            if provider == "openai":
                with openai.OpenAI(
                    api_key="test",
                    base_url="https://example.test/v1",
                    max_retries=0,
                    http_client=http,
                ) as client:
                    initial = client.chat.completions.create(
                        model="fake",
                        messages=[{"role": "user", "content": "lookup"}],
                        tools=[
                            {
                                "type": "function",
                                "function": {
                                    "name": "lookup",
                                    "parameters": {"type": "object", "properties": {}},
                                },
                            }
                        ],
                    )
                    tool = initial.choices[0].message.tool_calls[0]
                    value = lookup(**json.loads(tool.function.arguments))
                    final = client.chat.completions.create(
                        model="fake",
                        messages=[
                            {"role": "user", "content": "lookup"},
                            initial.choices[0].message.model_dump(exclude_none=True),
                            {
                                "role": "tool",
                                "tool_call_id": tool.id,
                                "content": json.dumps(value),
                            },
                        ],
                    )
                    assert final.choices[0].message.content == "done"
            else:
                with anthropic.Anthropic(
                    api_key="test",
                    base_url="https://example.test",
                    max_retries=0,
                    http_client=http,
                ) as client:
                    initial = client.messages.create(
                        model="fake",
                        max_tokens=32,
                        messages=[{"role": "user", "content": "lookup"}],
                        tools=[
                            {
                                "name": "lookup",
                                "input_schema": {"type": "object", "properties": {}},
                            }
                        ],
                    )
                    tool = initial.content[0]
                    value = lookup(**tool.input)
                    final = client.messages.create(
                        model="fake",
                        max_tokens=32,
                        messages=[
                            {"role": "user", "content": "lookup"},
                            {"role": "assistant", "content": [tool.model_dump()]},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool.id,
                                        "content": json.dumps(value),
                                    }
                                ],
                            },
                        ],
                    )
                    assert final.content[0].text == "done"
            assert json.dumps(value) == json.dumps(result())
    assert calls == 2 and tool_calls == 1
    assert validate_v2_cassette(path)["ok"]
    scrub(path)
    assert validate_v2_cassette(path)["ok"]
    _, interactions = CassetteStore(path).load()
    assert json.dumps(interactions[1].response["result"]) == json.dumps(result())
