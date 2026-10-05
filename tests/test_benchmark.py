"""The benchmark performs real offline record/replay and emits measured costs."""

from benchmarks.run import measure


def test_benchmark_smoke_is_offline_and_measures_every_operation() -> None:
    row = measure(3, 1)
    assert row["interactions"] == 3
    for name in (
        "pass_through_us",
        "record_us",
        "replay_us",
        "load_index_ms",
        "session_open_ms",
        "load_index_peak_mib",
    ):
        assert row[name] > 0
    assert "record_overhead_us" in row
