"""Measure transport and cassette costs offline without writing into the repo."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

import httpx2

import agentrec
from agentrec.cassette.replay import ReplayIndex
from agentrec.cassette.store import CassetteStore


def upstream(request: httpx2.Request) -> httpx2.Response:
    """Return a fixed response with no socket or provider access."""
    return httpx2.Response(200, json={"answer": "fixed"})


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds from a perf-counter start."""
    return (time.perf_counter() - start) * 1000


def measure(size: int, repeats: int = 3) -> dict[str, Any]:
    """Measure median latency and separate traced loader memory for one size."""
    measurements: dict[str, list[float]] = {
        name: []
        for name in (
            "pass_through_us",
            "record_us",
            "replay_us",
            "load_index_ms",
            "session_open_ms",
        )
    }
    with tempfile.TemporaryDirectory(prefix="agentrec-benchmark-") as directory:
        path = Path(directory) / "cassette"
        for _ in range(repeats):
            with httpx2.Client(transport=httpx2.MockTransport(upstream)) as client:
                start = time.perf_counter()
                for _ in range(size):
                    client.post("https://example.test/run", json={"prompt": "same"})
                measurements["pass_through_us"].append(elapsed_ms(start) * 1000 / size)
            with (
                agentrec.session(path, mode="all") as rec,
                httpx2.Client(
                    transport=rec.transport(httpx2.MockTransport(upstream))
                ) as client,
            ):
                start = time.perf_counter()
                for _ in range(size):
                    client.post("https://example.test/run", json={"prompt": "same"})
                measurements["record_us"].append(elapsed_ms(start) * 1000 / size)
            start = time.perf_counter()
            metadata, interactions = CassetteStore(path).load()
            index = ReplayIndex(interactions)
            measurements["load_index_ms"].append(elapsed_ms(start))
            assert len(index.interactions) == metadata.interaction_count == size
            start = time.perf_counter()
            rec = agentrec.session(path, mode="none")
            measurements["session_open_ms"].append(elapsed_ms(start))
            with rec, httpx2.Client(transport=rec.transport()) as client:
                start = time.perf_counter()
                for _ in range(size):
                    client.post("https://example.test/run", json={"prompt": "same"})
                measurements["replay_us"].append(elapsed_ms(start) * 1000 / size)
                assert rec.play_count == size
        del interactions, index, rec, client
        gc.collect()
        tracemalloc.start()
        _, interactions = CassetteStore(path).load()
        index = ReplayIndex(interactions)
        assert len(index.interactions) == size
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    row: dict[str, Any] = {"interactions": size}
    row.update(
        {
            name: round(statistics.median(values), 3)
            for name, values in measurements.items()
        }
    )
    row["record_overhead_us"] = round(row["record_us"] - row["pass_through_us"], 3)
    row["load_index_peak_mib"] = round(peak / (1024 * 1024), 3)
    return row


def main() -> None:
    """Print reproducible JSON measurements with platform and Python details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 1000, 10000])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1 or any(size < 1 for size in args.sizes):
        parser.error("sizes and repeats must be positive")
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "architecture": platform.machine(),
                "repeats": args.repeats,
                "rows": [measure(size, args.repeats) for size in args.sizes],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
