"""Tiny offline math flow demonstrating record and replay."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentrec._legacy.core import AgentRecorder, AgentReplayer
from agentrec._legacy.models import RunRecord
from agentrec._legacy.providers import FakeModelProvider, ModelRequest
from agentrec._legacy.store import CassetteStore
from agentrec._legacy.tools import default_tool_registry


def record_math_flow(run_path: str | Path, expression: str = "2+3") -> dict[str, Any]:
    """Record a simple math task into a cassette."""

    store = CassetteStore(run_path)
    recorder = AgentRecorder(
        store=store,
        run=RunRecord(
            run_id="math_flow",
            task=f"Calculate {expression}",
        ),
        provider=FakeModelProvider(),
        tools=default_tool_registry(),
    )
    request = _model_request(expression)

    model_response = recorder.record_model_call(request)
    tool_result = recorder.record_tool_call("calculator", {"expression": expression})
    final_output = str(tool_result.output["result"])
    recorder.finish(final_output)

    return {
        "mode": "record",
        "expression": expression,
        "model_output": model_response.output_text,
        "tool_output": tool_result.output,
        "final_output": final_output,
        "step_count": len(store.read_steps()),
    }


def replay_math_flow(run_path: str | Path, expression: str = "2+3") -> dict[str, Any]:
    """Replay a simple math task from a cassette."""

    store = CassetteStore(run_path)
    replayer = AgentReplayer(store)
    request = _model_request(expression)

    model_response = replayer.replay_model_call(request)
    tool_result = replayer.replay_tool_call("calculator", {"expression": expression})
    final_output = replayer.read_final_output()

    return {
        "mode": "replay",
        "expression": expression,
        "model_output": model_response.output_text,
        "tool_output": tool_result.output,
        "final_output": final_output,
        "step_count": len(store.read_steps()),
    }


def _model_request(expression: str) -> ModelRequest:
    return ModelRequest(
        model="fake-math",
        messages=[{"role": "user", "content": f"calculate {expression}"}],
    )
