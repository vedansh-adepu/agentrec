"""Require at least 90% branch coverage from coverage.py JSON totals."""

import json
import sys
from pathlib import Path


def main() -> None:
    """Fail CI if fewer than 90% of the measured branches execute."""
    totals = json.loads(Path(sys.argv[1]).read_text())["totals"]
    covered = totals["covered_branches"]
    count = totals["num_branches"]
    percentage = 100 * covered / count if count else 0
    print(f"Branch coverage: {covered}/{count} = {percentage:.2f}%")
    if percentage < 90:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
