from pathlib import Path

import pytest

from agentrec.errors import CassetteNotFoundError, CassetteValidationError
from agentrec.models import CachedInteraction, RunRecord, Step, Usage
from agentrec.store import CassetteStore


def make_run() -> RunRecord:
    return RunRecord(run_id="run_001", task="add 2 and 3", final_output="5")


def make_step(index: int = 0) -> Step:
    return Step(
        index=index,
        kind="tool",
        name="calculator",
        request_hash=f"hash_{index}",
        input={"expression": "2+3"},
        output={"result": 5},
        latency_ms=1.0,
        usage=Usage(),
    )


def make_interaction() -> CachedInteraction:
    return CachedInteraction(
        request_hash="abc123",
        kind="tool",
        request={"name": "calculator", "arguments": {"expression": "2+3"}},
        response={"result": 5},
        latency_ms=1.5,
    )


def test_initialize_creates_expected_folder_structure(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")

    store.initialize(make_run())

    assert (tmp_path / "cassette" / "metadata.json").is_file()
    assert (tmp_path / "cassette" / "trace.jsonl").is_file()
    assert (tmp_path / "cassette" / "responses").is_dir()
    assert (tmp_path / "cassette" / "artifacts").is_dir()


def test_write_and_read_metadata_round_trips_run_record(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")
    run = make_run()

    store.initialize(run)
    store.write_metadata(run)

    assert store.read_metadata() == run


def test_append_and_read_steps_round_trips_steps_in_order(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")
    first = make_step(index=0)
    second = make_step(index=1)

    store.initialize(make_run())
    store.append_step(first)
    store.append_step(second)

    assert store.read_steps() == [first, second]


def test_write_and_read_interaction_round_trips_cached_interaction(
    tmp_path: Path,
) -> None:
    store = CassetteStore(tmp_path / "cassette")
    interaction = make_interaction()

    store.initialize(make_run())
    path = store.write_interaction(interaction)

    assert path == tmp_path / "cassette" / "responses" / "abc123_tool.json"
    assert store.read_interaction("abc123", "tool") == interaction


def test_read_interaction_raises_for_missing_hash(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")

    store.initialize(make_run())

    with pytest.raises(CassetteNotFoundError):
        store.read_interaction("missing", "model")


def test_write_and_read_final_output_round_trips_text(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")

    store.initialize(make_run())
    path = store.write_final_output("The answer is 5.")

    assert path == tmp_path / "cassette" / "artifacts" / "final_output.txt"
    assert store.read_final_output() == "The answer is 5."


def test_validate_passes_for_valid_cassette(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")

    store.initialize(make_run())

    store.validate()


def test_validate_raises_for_broken_cassette(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")

    (tmp_path / "cassette" / "responses").mkdir(parents=True)
    (tmp_path / "cassette" / "artifacts").mkdir()

    with pytest.raises(CassetteValidationError):
        store.validate()
