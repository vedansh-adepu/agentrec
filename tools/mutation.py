"""Run mutation testing in an isolated temporary copy; preserve result paths."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """Copy sources/tests and run mutmut without mutating the checkout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=("canonical", "matching", "replay"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = Path(tempfile.mkdtemp(prefix="agentrec-mutation-"))
    for name in ("src", "tests", "docs"):
        shutil.copytree(
            root / name,
            target / name,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
        )
    shutil.copy2(root / "pyproject.toml", target / "pyproject.toml")
    if args.module:
        module = "cassette/replay" if args.module == "replay" else args.module
        configuration = target / "pyproject.toml"
        text = re.sub(
            r"(?m)^only_mutate = .*?$",
            f'only_mutate = ["src/agentrec/{module}.py"]',
            configuration.read_text(),
        )
        configuration.write_text(text)
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
