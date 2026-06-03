"""Built-in offline tools."""

from __future__ import annotations

import ast
import operator
from typing import Any

from agentrec.errors import AgentRecError
from agentrec.tools.registry import ToolRegistry

BinaryOperator = type[ast.Add | ast.Sub | ast.Mult | ast.Div]
UnaryOperator = type[ast.UAdd | ast.USub]

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculator_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a simple arithmetic expression safely."""

    expression = arguments.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise AgentRecError("Calculator requires a non-empty expression string")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate_node(tree.body)
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise AgentRecError(f"Invalid calculator expression: {expression}") from exc

    return {"result": result}


def default_tool_registry() -> ToolRegistry:
    """Return a registry with built-in tools registered."""

    registry = ToolRegistry()
    registry.register("calculator", calculator_tool)
    return registry


def _evaluate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise ValueError("Only numeric constants are allowed")
        return node.value

    if isinstance(node, ast.BinOp):
        operator_func = _BINARY_OPERATORS.get(type(node.op))
        if operator_func is None:
            raise ValueError("Unsupported binary operator")
        return operator_func(_evaluate_node(node.left), _evaluate_node(node.right))

    if isinstance(node, ast.UnaryOp):
        operator_func = _UNARY_OPERATORS.get(type(node.op))
        if operator_func is None:
            raise ValueError("Unsupported unary operator")
        return operator_func(_evaluate_node(node.operand))

    raise ValueError("Unsupported expression")
