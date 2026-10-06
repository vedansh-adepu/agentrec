"""Core data models for recorded agent runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CASSETTE_SCHEMA_VERSION = "1"


class AgentRecModel(BaseModel):
    """Base model with deterministic JSON-friendly defaults."""

    model_config = ConfigDict(extra="forbid")


class Usage(AgentRecModel):
    """Token and cost information for a recorded interaction."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class Step(AgentRecModel):
    """One ordered event in an agent run trace."""

    index: int
    kind: Literal["model", "tool", "final"]
    name: str
    request_hash: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    usage: Usage | None = None


class CachedInteraction(AgentRecModel):
    """A request/response pair stored for future replay."""

    request_hash: str
    kind: Literal["model", "tool"]
    request: dict[str, Any]
    response: dict[str, Any]
    usage: Usage | None = None
    latency_ms: float | None = None


class RunRecord(AgentRecModel):
    """Serializable summary of one recorded agent run."""

    schema_version: str = CASSETTE_SCHEMA_VERSION
    run_id: str
    task: str
    steps: list[Step] = Field(default_factory=list)
    final_output: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
