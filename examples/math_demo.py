"""Run the offline agentrec math demo without live API calls.

Usage:
    python examples/math_demo.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from agentrec.examples import record_math_flow, replay_math_flow


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        run_path = Path(temp_dir) / "math_run"
        recorded = record_math_flow(run_path, expression="2+3")
        replayed = replay_math_flow(run_path, expression="2+3")

    print(f"recorded_final_output={recorded['final_output']}")
    print(f"replayed_final_output={replayed['final_output']}")


if __name__ == "__main__":
    main()
