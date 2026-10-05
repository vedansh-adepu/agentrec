"""Stable diagnostics and privacy-safe logging regressions."""

import logging
from pathlib import Path

import pytest

import agentrec
from agentrec import errors
from agentrec.canonical import CanonicalValueError
from agentrec.cassette import store
from agentrec.matching import MatchPolicyError


def test_every_agentrec_error_has_documented_unique_code_and_hint() -> None:
    documented = (Path(__file__).parents[1] / "docs/errors.md").read_text()
    classes = {
        value
        for module in (errors, store)
        for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, errors.AgentRecError)
    }
    classes.update({CanonicalValueError, MatchPolicyError})
    codes = set()
    for cls in classes:
        assert cls.code not in codes
        codes.add(cls.code)
        assert cls.code in documented and cls.__name__ in documented
        exc = (
            cls("OriginalError", "first\nsecond")
            if cls is errors.ReplayedToolError
            else cls("first\nsecond")
        )
        lines = str(exc).splitlines()
        assert len(lines) == 2
        assert lines[0].startswith(cls.code + " ")
        assert lines[1].startswith("hint: ") and cls.hint


def test_debug_logs_contain_keys_without_private_values(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="agentrec")
    path = tmp_path / "log"
    for mode in ("once", "none"):
        with agentrec.session(path, mode=mode) as rec:

            @rec.tool
            def sensitive(value: str) -> str:
                return value

            assert sensitive("private-personal-value") == "private-personal-value"
    assert "recorded key=" in caplog.text and "replay hit key=" in caplog.text
    assert "private-personal-value" not in caplog.text
