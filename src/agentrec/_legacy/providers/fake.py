"""Deterministic offline model provider."""

from __future__ import annotations

from agentrec._legacy.models import Usage
from agentrec._legacy.providers.base import ModelRequest, ModelResponse


class FakeModelProvider:
    """A model provider that returns predictable local responses."""

    def __init__(self, response_map: dict[str, str] | None = None) -> None:
        self.response_map = response_map or {}

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return a deterministic response without making network calls."""

        prompt = self._last_user_message(request)
        output_text = self.response_map.get(
            prompt,
            f"Use the calculator tool for: {prompt}",
        )
        return ModelResponse(
            model=request.model,
            output_text=output_text,
            usage=Usage(
                input_tokens=self._count_input_tokens(request),
                output_tokens=len(output_text.split()),
                total_tokens=self._count_input_tokens(request)
                + len(output_text.split()),
                cost_usd=0.0,
            ),
            raw={"provider": "fake"},
        )

    def _last_user_message(self, request: ModelRequest) -> str:
        for message in reversed(request.messages):
            if message.get("role") == "user":
                return message.get("content", "")
        if request.messages:
            return request.messages[-1].get("content", "")
        return ""

    def _count_input_tokens(self, request: ModelRequest) -> int:
        return sum(
            len(message.get("content", "").split()) for message in request.messages
        )
