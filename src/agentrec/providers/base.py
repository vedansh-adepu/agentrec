"""Base types for model providers."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from agentrec.models import Usage


class ModelRequest(BaseModel):
    """Input sent to a model provider."""

    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[dict[str, str]]
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Output returned by a model provider."""

    model_config = ConfigDict(extra="forbid")

    model: str
    output_text: str
    usage: Usage | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelProvider(Protocol):
    """Protocol implemented by model providers."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return a model response for a request."""
