"""Simple deterministic tool registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentrec.errors import AgentRecError

ToolCallable = Callable[[dict[str, Any]], dict[str, Any]]


class ToolResult(BaseModel):
    """JSON-serializable result of a tool call."""

    model_config = ConfigDict(extra="forbid")

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    """Registry for named local tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}

    def register(self, name: str, func: ToolCallable) -> None:
        """Register a callable tool by name."""

        if not name:
            raise AgentRecError("Tool name must not be empty")
        self._tools[name] = func

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a registered tool by name."""

        if name not in self._tools:
            raise AgentRecError(f"Unknown tool: {name}")

        output = self._tools[name](arguments)
        return ToolResult(name=name, arguments=arguments, output=output)

    def list_tools(self) -> list[str]:
        """Return registered tool names in deterministic order."""

        return sorted(self._tools)
