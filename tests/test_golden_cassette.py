"""Golden schema-v2 bytes and occurrence replay protect format compatibility."""

from pathlib import Path

import agentrec
from agentrec.cassette.store import CassetteStore
from agentrec.validation import validate_v2_cassette

GOLDEN = Path(__file__).parent / "data/golden-v2"


def test_golden_cassette_validates_and_roundtrips_exact_bytes(tmp_path: Path) -> None:
    assert validate_v2_cassette(GOLDEN)["ok"]
    metadata, interactions = CassetteStore(GOLDEN).load()
    CassetteStore(tmp_path / "copy").save(metadata, interactions)
    for name in ("cassette.json", "interactions.jsonl"):
        assert (tmp_path / "copy" / name).read_bytes() == (GOLDEN / name).read_bytes()


def test_golden_cassette_replays_distinct_tool_occurrences() -> None:
    with agentrec.session(GOLDEN, mode="none") as rec:

        @rec.tool
        def lookup(model: str) -> dict:
            raise AssertionError("executed golden replay tool")

        assert lookup("F-100") == {"part": "IGN-9", "stock": 3}
        assert lookup("F-100") == {"part": "IGN-9", "stock": 0}
        assert rec.all_played and rec.play_count == 2
