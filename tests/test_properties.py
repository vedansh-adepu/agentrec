"""Generated invariants for matching, occurrence replay, and redaction."""

import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agentrec.canonical import canonical_json, canonical_sha256, decode_canonical
from agentrec.cassette.model import Interaction
from agentrec.cassette.replay import ReplayIndex
from agentrec.errors import ReplayExhaustedError
from agentrec.matching import MatchPolicy
from agentrec.redaction import BUILTIN_PATTERNS, Redactor

scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)
values = st.recursive(
    scalars,
    lambda child: (
        st.lists(child, max_size=5) | st.dictionaries(st.text(), child, max_size=5)
    ),
    max_leaves=15,
)


@settings(max_examples=80, deadline=None, database=None)
@given(st.dictionaries(st.text(), values, max_size=8))
def test_canonical_idempotent_and_dict_order_insensitive(value):
    encoded = canonical_json(value)
    assert canonical_json(decode_canonical(encoded)) == encoded
    assert canonical_sha256(dict(reversed(list(value.items())))) == canonical_sha256(
        value
    )
    assert MatchPolicy().tool_key("lookup", value) == MatchPolicy().tool_key(
        "lookup", dict(reversed(list(value.items())))
    )


@settings(max_examples=10, deadline=None, database=None)
@given(values)
def test_generated_key_stable_across_processes(value):
    code = (
        "import json,sys; from agentrec.canonical import canonical_sha256; "
        "print(canonical_sha256(json.loads(sys.argv[1])))"
    )
    result = subprocess.check_output(
        [sys.executable, "-c", code, json.dumps(value)], text=True
    ).strip()
    assert result == canonical_sha256(value)


@settings(max_examples=80, deadline=None, database=None)
@given(st.lists(st.integers(min_value=0, max_value=4), max_size=30))
def test_generated_occurrences_replay_fifo(sequence):
    counts = Counter()
    entries = []
    for seq, group in enumerate(sequence):
        key = str(group) * 64
        entries.append(
            Interaction(
                seq=seq,
                kind="tool",
                key=key,
                occurrence=counts[group],
                key_inputs_redacted=False,
                request={"name": str(group), "arguments": {}},
                response={"result": seq},
                started_at=datetime.now(UTC),
                duration_ms=0,
            )
        )
        counts[group] += 1
    index = ReplayIndex(entries)
    for group in sorted(counts, reverse=True):
        expected = [entry for entry in entries if entry.key == str(group) * 64]
        assert [index.play(entry.key, entry.request).seq for entry in expected] == [
            entry.seq for entry in expected
        ]
        with pytest.raises(ReplayExhaustedError):
            index.play(str(group) * 64, {"name": str(group), "arguments": {}})
    assert index.play_count == len(sequence)
    assert index.all_played
    index.assert_all_played()


@settings(max_examples=80, deadline=None, database=None)
@given(st.sampled_from(list(BUILTIN_PATTERNS)), st.data())
def test_redaction_leaves_no_builtin_pattern(rule, data):
    secret = data.draw(st.from_regex(BUILTIN_PATTERNS[rule], fullmatch=True))
    redacted = Redactor().redact_text("prefix " + secret + " suffix")
    assert all(
        pattern.search(redacted) is None for pattern in BUILTIN_PATTERNS.values()
    )
