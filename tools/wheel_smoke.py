"""Smoke-test an installed wheel with core dependencies only, offline."""

import importlib.metadata
import tempfile
from pathlib import Path

import agentrec


def main() -> None:
    """Verify distribution version and tool record/replay without optional SDKs."""
    assert importlib.metadata.version("agentrec") == agentrec.__version__
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "smoke"
        with agentrec.session(path, mode="once") as rec:

            @rec.tool
            def lookup(value: int) -> int:
                return value + 1

            assert lookup(1) == 2
        with agentrec.session(path, mode="none") as rec:

            @rec.tool
            def lookup(value: int) -> int:
                raise AssertionError("wheel replay executed tool")

            assert lookup(1) == 2
            assert rec.all_played
    print("wheel smoke: version and offline tool replay passed")


if __name__ == "__main__":
    main()
