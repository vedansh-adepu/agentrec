import pytest

from agentrec.errors import AgentRecError
from agentrec.tools import ToolRegistry, calculator_tool, default_tool_registry


def test_tool_registry_can_register_and_call_tool() -> None:
    registry = ToolRegistry()
    registry.register("echo", lambda arguments: {"echo": arguments["text"]})

    result = registry.call("echo", {"text": "hello"})

    assert result.name == "echo"
    assert result.arguments == {"text": "hello"}
    assert result.output == {"echo": "hello"}


def test_list_tools_returns_registered_names() -> None:
    registry = ToolRegistry()
    registry.register("b", lambda arguments: arguments)
    registry.register("a", lambda arguments: arguments)

    assert registry.list_tools() == ["a", "b"]


def test_unknown_tool_raises_error() -> None:
    registry = ToolRegistry()

    with pytest.raises(AgentRecError):
        registry.call("missing", {})


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("17 * 23", 391),
        ("2+3", 5),
        ("10 / 2", 5),
        ("-(2 + 3)", -5),
    ],
)
def test_calculator_handles_basic_arithmetic(
    expression: str,
    expected: int | float,
) -> None:
    assert calculator_tool({"expression": expression}) == {"result": expected}


def test_calculator_rejects_unsafe_expressions() -> None:
    with pytest.raises(AgentRecError):
        calculator_tool({"expression": "__import__('os').system('rm -rf /')"})


def test_default_tool_registry_includes_calculator() -> None:
    registry = default_tool_registry()

    assert registry.list_tools() == ["calculator"]
    assert registry.call("calculator", {"expression": "2+3"}).output == {"result": 5}
