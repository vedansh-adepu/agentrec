"""Run mutation testing in an isolated temporary copy; preserve result paths."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """Copy sources/tests and run mutmut without mutating the checkout."""
    root = Path(__file__).resolve().parents[1]
    target = Path(tempfile.mkdtemp(prefix="agentrec-mutation-"))
    for name in ("src", "tests", "docs"):
        shutil.copytree(
            root / name,
            target / name,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
        )
    shutil.copy2(root / "pyproject.toml", target / "pyproject.toml")
    print(f"Mutation workspace: {target}", flush=True)
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "mutmut", "run", "--max-children", "2"],
        cwd=target,
        env=env,
        check=False,
    )
    subprocess.run(
        [sys.executable, "-m", "mutmut", "results"], cwd=target, env=env, check=False
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
