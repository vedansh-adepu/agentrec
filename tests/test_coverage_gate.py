"""CI must reject low branch coverage even when total coverage is high."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "covered,count,exit_code", [(89, 100, 1), (90, 100, 0), (0, 0, 1)]
)
def test_branch_gate_threshold(
    tmp_path: Path, covered: int, count: int, exit_code: int
) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_branches": covered,
                    "num_branches": count,
                    "percent_covered": 99,
                }
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "tools/coverage_gate.py"),
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == exit_code
    assert "Branch coverage:" in result.stdout
