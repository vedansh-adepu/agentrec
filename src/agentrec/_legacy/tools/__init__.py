"""Tool registry and built-in tools."""

from agentrec._legacy.tools.builtin import calculator_tool, default_tool_registry
from agentrec._legacy.tools.registry import ToolRegistry, ToolResult

__all__ = [
    "ToolRegistry",
    "ToolResult",
    "calculator_tool",
    "default_tool_registry",
]
