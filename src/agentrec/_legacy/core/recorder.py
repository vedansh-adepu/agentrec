"""Offline recorder for model and tool calls."""

from __future__ import annotations

import time
from typing import Any

from agentrec._legacy.hashing import hash_request
from agentrec._legacy.models import CachedInteraction, RunRecord, Step
from agentrec._legacy.providers.base import ModelProvider, ModelRequest, ModelResponse
from agentrec._legacy.store import CassetteStore
from agentrec._legacy.tools import ToolRegistry, ToolResult


class AgentRecorder:
    """Record offline model and tool calls into a cassette store."""

    def __init__(
        self,
        store: CassetteStore,
        run: RunRecord,
        provider: ModelProvider,
        tools: ToolRegistry,
    ) -> None:
        self.store = store
        self.run = run
        self.provider = provider
        self.tools = tools
        self._step_index = 0
        self.store.initialize(run)

    def record_model_call(self, request: ModelRequest) -> ModelResponse:
        """Call the model provider and record the interaction."""

        request_dict = request.model_dump(mode="json")
        request_hash = hash_request(request_dict)

        started_at = time.perf_counter()
        response = self.provider.complete(request)
        latency_ms = (time.perf_counter() - started_at) * 1000
        response_dict = response.model_dump(mode="json")

        interaction = CachedInteraction(
            request_hash=request_hash,
            kind="model",
            request=request_dict,
            response=response_dict,
            usage=response.usage,
            latency_ms=latency_ms,
        )
        self.store.write_interaction(interaction)
        self._append_step(
            Step(
                index=self._next_step_index(),
                kind="model",
                name=request.model,
                request_hash=request_hash,
                input=request_dict,
                output=response_dict,
                latency_ms=latency_ms,
                usage=response.usage,
            ),
        )
        return response

    def record_tool_call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a registered tool and record the interaction."""

        request_dict = {"name": name, "arguments": arguments}
        request_hash = hash_request(request_dict)

        started_at = time.perf_counter()
        result = self.tools.call(name, arguments)
        latency_ms = (time.perf_counter() - started_at) * 1000
        result_dict = result.model_dump(mode="json")

        interaction = CachedInteraction(
            request_hash=request_hash,
            kind="tool",
            request=request_dict,
            response=result_dict,
            usage=None,
            latency_ms=latency_ms,
        )
        self.store.write_interaction(interaction)
        self._append_step(
            Step(
                index=self._next_step_index(),
                kind="tool",
                name=name,
                request_hash=request_hash,
                input=request_dict,
                output=result_dict,
                latency_ms=latency_ms,
                usage=None,
            ),
        )
        return result

    def finish(self, final_output: str) -> None:
        """Record final output and update run metadata."""

        self.store.write_final_output(final_output)
        self.run.final_output = final_output
        self._append_step(
            Step(
                index=self._next_step_index(),
                kind="final",
                name="final_output",
                request_hash=None,
                input={},
                output={"content": final_output},
            ),
        )
        self.store.write_metadata(self.run)

    def _next_step_index(self) -> int:
        index = self._step_index
        self._step_index += 1
        return index

    def _append_step(self, step: Step) -> None:
        self.run.steps.append(step)
        self.store.append_step(step)
