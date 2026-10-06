"""Pytest fixture and marker for agentrec cassette sessions."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from .modes import RecordMode
from .session import Session


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register a command-line override for agentrec fixture record mode."""
    group = parser.getgroup("agentrec")
    group.addoption(
        "--agentrec-mode",
        action="store",
        choices=[mode.value for mode in RecordMode],
        default=None,
        help="Cassette mode for agentrec_session fixtures.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Document the optional agentrec marker to pytest."""
    config.addinivalue_line(
        "markers",
        "agentrec(cassette=None): opt into a named agentrec cassette.",
    )


def default_mode() -> RecordMode:
    """Choose AGENTREC_MODE, else replay-only in CI and once locally."""
    selected = os.getenv("AGENTREC_MODE")
    if selected is not None:
        return RecordMode(selected)
    return RecordMode.NONE if os.getenv("CI") else RecordMode.ONCE


def cassette_name(nodeid: str, explicit: str | None = None) -> str:
    """Produce a safe stable filename from a test id or explicit marker name."""
    if explicit is not None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit) or explicit in {
            ".",
            "..",
        }:
            raise ValueError("cassette marker name must be a safe filename")
        return explicit
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", nodeid).strip("-")[:80]
    digest = hashlib.sha256(nodeid.encode()).hexdigest()[:10]
    return f"{slug}-{digest}"


@pytest.fixture
def agentrec_session(request: pytest.FixtureRequest) -> Iterator[Session]:
    """Yield a cassette session named from the test node or agentrec marker."""
    marker = request.node.get_closest_marker("agentrec")
    name: str | None = None
    if marker is not None:
        named = marker.kwargs.get("cassette")
        if named is not None and not isinstance(named, str):
            raise ValueError("cassette marker name must be a string")
        name = named
    path = (
        Path(request.config.rootpath)
        / "tests"
        / "cassettes"
        / cassette_name(request.node.nodeid, name)
    )
    option = request.config.getoption("agentrec_mode")
    mode = RecordMode(option) if option is not None else default_mode()
    with Session(path, mode=mode) as active:
        yield active
