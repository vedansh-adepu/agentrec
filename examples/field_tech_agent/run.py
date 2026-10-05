"""Exercise model and tool replay with a fake furnace-diagnosis agent."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx2
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletionFunctionToolParam

import agentrec
from agentrec.diff import diff_v2_cassettes
from agentrec.errors import ReplayMissError

MODEL = "field-tech-fake"
TOOLS: list[ChatCompletionFunctionToolParam] = cast(
    list[ChatCompletionFunctionToolParam],
    [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {arg: {"type": "string"}},
                    "required": [arg],
                },
            },
        }
        for name, description, arg in (
            ("lookup_equipment", "Look up a furnace model.", "model_number"),
            ("search_parts", "Find a replacement part.", "symptom"),
            ("create_work_order", "Create a repair work order.", "part_number"),
        )
    ],
)


def _tool_call(name: str, arguments: dict[str, str], index: int) -> dict[str, Any]:
    return {
        "id": f"call_{index}_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _completion(index: int) -> dict[str, Any]:
    if index == 1:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                _tool_call("lookup_equipment", {"model_number": "F-100"}, 1),
                _tool_call("search_parts", {"symptom": "no heat"}, 2),
            ],
        }
        finish_reason = "tool_calls"
    elif index == 2:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                _tool_call("search_parts", {"symptom": "no heat"}, 3),
                _tool_call("create_work_order", {"part_number": "IGN-9"}, 4),
            ],
        }
        finish_reason = "tool_calls"
    else:
        message = {
            "role": "assistant",
            "content": "Replace the IGN-9 igniter on furnace F-100.",
        }
        finish_reason = "stop"
    return {
        "id": f"chatcmpl-{index}",
        "object": "chat.completion",
        "created": 1,
        "model": MODEL,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
    }


class FakeLLM:
    """Produce three different chat completions for identical HTTP requests."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.calls += 1
        if self.calls > 3:
            raise AssertionError("unexpected fourth upstream model call")
        return httpx2.Response(200, json=_completion(self.calls))


def run_agent(
    rec: agentrec.Session,
    *,
    prompt: str,
    work_order_path: Path,
    variant: str = "base",
    upstream: FakeLLM | None = None,
) -> str:
    """Run one fixed three-step agent loop through an SDK and three tools."""
    search_calls = 0

    @rec.tool
    def lookup_equipment(model_number: str) -> dict[str, str]:
        return {"model": model_number, "igniter": "IGN-9"}

    @rec.tool
    def search_parts(symptom: str) -> dict[str, Any]:
        nonlocal search_calls
        search_calls += 1
        stock = (3 if search_calls == 1 else 0) + (1 if variant == "alternate" else 0)
        return {"symptom": symptom, "part": "IGN-9", "stock": stock}

    @rec.tool
    def create_work_order(part_number: str) -> dict[str, str]:
        work_order_path.write_text(f"Replace {part_number}\n")
        return {"work_order": "WO-100", "part": part_number}

    tools: dict[str, Callable[..., Any]] = {
        "lookup_equipment": lookup_equipment,
        "search_parts": search_parts,
        "create_work_order": create_work_order,
    }
    inner = httpx2.MockTransport(upstream or FakeLLM())
    client = OpenAI(
        api_key="test",
        base_url="https://offline.example.test/v1",
        max_retries=0,
        http_client=httpx2.Client(transport=rec.transport(inner)),
    )
    try:
        final = ""
        for _ in range(3):
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=TOOLS,
            )
            message = completion.choices[0].message
            for tool_call in message.tool_calls or []:
                if tool_call.type != "function":
                    continue
                arguments = json.loads(tool_call.function.arguments)
                tools[tool_call.function.name](**arguments)
            if message.content:
                final = message.content
        return final
    finally:
        client.close()


def run_demo() -> list[str]:
    """Run record, sealed replay, drift miss, and trajectory diff offline."""
    lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="agentrec-field-tech-") as directory:
        root = Path(directory)
        first = root / "first"
        second = root / "second"
        initial_work_order = root / "record-work-order.txt"
        replay_work_order = root / "replay-work-order.txt"
        source = FakeLLM()
        with agentrec.session(first, mode="once") as rec:
            recorded = run_agent(
                rec,
                prompt="F-100 furnace has no heat",
                work_order_path=initial_work_order,
                upstream=source,
            )
        lines.append(
            f"record: {recorded} model_calls={source.calls} "
            f"work_order={initial_work_order.exists()}"
        )

        forbidden = FakeLLM()
        with agentrec.session(first, mode="none") as rec:
            replayed = run_agent(
                rec,
                prompt="F-100 furnace has no heat",
                work_order_path=replay_work_order,
                upstream=forbidden,
            )
        lines.append(
            f"replay: {replayed} upstream_calls={forbidden.calls} "
            f"work_order={replay_work_order.exists()}"
        )

        with agentrec.session(first, mode="none", fail_on_unplayed=False) as rec:
            try:
                run_agent(
                    rec,
                    prompt="F-100 furnace has a different symptom",
                    work_order_path=replay_work_order,
                    upstream=forbidden,
                )
            except (ReplayMissError, openai.APIConnectionError) as exc:
                cause = exc if isinstance(exc, ReplayMissError) else exc.__cause__
                if not isinstance(cause, ReplayMissError):
                    raise
                lines.append(f"modified prompt: {cause}")

        with agentrec.session(second, mode="once") as rec:
            run_agent(
                rec,
                prompt="F-100 furnace has no heat",
                work_order_path=root / "second-work-order.txt",
                variant="alternate",
            )
        change = diff_v2_cassettes(first, second)
        lines.append(
            f"diff: steps={change['steps']} changed={change['changed']} "
            f"added={change['added']} removed={change['removed']}"
        )
    return lines


if __name__ == "__main__":
    for line in run_demo():
        print(line)
