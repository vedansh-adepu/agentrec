"""Hermetic replay from cached cassette interactions."""

from __future__ import annotations

from typing import Any

from agentrec.errors import CassetteNotFoundError, ReplayMissError
from agentrec.hashing import hash_request
from agentrec.providers.base import ModelRequest, ModelResponse
from agentrec.store import CassetteStore
from agentrec.tools import ToolResult


class AgentReplayer:
    """Replay model and tool calls from a cassette without live calls."""

    def __init__(self, store: CassetteStore) -> None:
        self.store = store
        self.store.validate()
        self.metadata = self.store.read_metadata()

    def replay_model_call(self, request: ModelRequest) -> ModelResponse:
        """Return the cached model response for a request."""

        request_dict = request.model_dump(mode="json")
        request_hash = hash_request(request_dict)
        try:
            interaction = self.store.read_interaction(request_hash, "model")
        except CassetteNotFoundError as exc:
            msg = f"Replay miss for model request {request.model}: {request_hash}"
            raise ReplayMissError(msg) from exc
        return ModelResponse.model_validate(interaction.response)

    def replay_tool_call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Return the cached tool result for a request."""

        request_dict = {"name": name, "arguments": arguments}
        request_hash = hash_request(request_dict)
        try:
            interaction = self.store.read_interaction(request_hash, "tool")
        except CassetteNotFoundError as exc:
            msg = f"Replay miss for tool request {name}: {request_hash}"
            raise ReplayMissError(msg) from exc
        return ToolResult.model_validate(interaction.response)

    def read_final_output(self) -> str:
        """Read the recorded final output without mutating the cassette."""

        return self.store.read_final_output()
