"""End-to-end pytest plugin tests in a generated temporary project."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentrec.pytest_plugin import cassette_name, default_mode

pytest_plugins = ("pytester",)


def test_plugin_mode_default_respects_ci_and_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("AGENTREC_MODE", raising=False)
    assert default_mode().value == "once"
    monkeypatch.setenv("CI", "1")
    assert default_mode().value == "none"
    monkeypatch.setenv("AGENTREC_MODE", "all")
    assert default_mode().value == "all"


def test_cassette_name_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        cassette_name("node", "../outside")
    assert cassette_name("tests/test_x.py::test_y").startswith(
        "tests-test_x-py-test_y-"
    )


def test_fixture_records_then_replays_without_executing_tool(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        test_sample="""
import pytest

@pytest.mark.agentrec(cassette="named")
def test_record(agentrec_session):
    @agentrec_session.tool
    def lookup(value: int) -> int:
        return value + 1
    assert lookup(2) == 3
"""
    )
    first = pytester.runpytest_subprocess("--agentrec-mode=once", "-q")
    first.assert_outcomes(passed=1)
    cassette = Path(pytester.path) / "tests" / "cassettes" / "named"
    assert (cassette / "cassette.json").is_file()
    pytester.makepyfile(
        test_sample="""
import pytest

@pytest.mark.agentrec(cassette="named")
def test_record(agentrec_session):
    @agentrec_session.tool
    def lookup(value: int) -> int:
        raise AssertionError("executed")
    assert lookup(2) == 3
"""
    )
    second = pytester.runpytest_subprocess("--agentrec-mode=none", "-q")
    second.assert_outcomes(passed=1)
