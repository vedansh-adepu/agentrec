"""Regression tests for canonical values and explicit match policy."""

import math
import subprocess
import sys

import pytest

from agentrec.canonical import (
    CanonicalValueError,
    canonical_json,
    canonical_sha256,
    decode_canonical,
)
from agentrec.matching import MatchPolicy, MatchPolicyError


def test_mapping_order_is_irrelevant_but_list_order_is_not() -> None:
    assert canonical_sha256({"a": 1, "b": [2, 3]}) == canonical_sha256(
        {"b": [2, 3], "a": 1}
    )
    assert canonical_sha256([1, 2]) != canonical_sha256([2, 1])


def test_integer_and_float_have_distinct_keys() -> None:
    assert canonical_sha256({"value": 1}) != canonical_sha256({"value": 1.0})


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_special_floats_round_trip(value: float) -> None:
    restored = decode_canonical(canonical_json({"value": value}))
    assert isinstance(restored, dict)
    assert isinstance(restored["value"], float)
    if math.isnan(value):
        assert math.isnan(restored["value"])
    else:
        assert restored["value"] == value


def test_reserved_looking_user_dictionary_does_not_collide_with_float_tag() -> None:
    assert canonical_sha256({"$float": "inf"}) != canonical_sha256(float("inf"))


@pytest.mark.parametrize("value", [{1: "x"}, (1, 2), object()])
def test_unknown_types_are_rejected(value: object) -> None:
    with pytest.raises(CanonicalValueError):
        canonical_json(value)


def test_key_is_stable_across_processes() -> None:
    expression = (
        "from agentrec.canonical import canonical_sha256; "
        "print(canonical_sha256({'x': [1, 2.0]}))"
    )
    result = subprocess.check_output(
        [sys.executable, "-c", expression], text=True
    ).strip()
    assert result == canonical_sha256({"x": [1, 2.0]})


def test_nested_timestamp_is_meaningful_by_default() -> None:
    policy = MatchPolicy()
    assert policy.tool_key(
        "lookup", {"metadata": {"timestamp": "one"}}
    ) != policy.tool_key("lookup", {"metadata": {"timestamp": "two"}})


def test_only_explicit_pointer_is_ignored() -> None:
    policy = MatchPolicy(ignore_body_paths=("/metadata/request_id",))
    headers = {"content-type": "application/json"}
    first = b'{"metadata":{"request_id":"a","timestamp":"one"}}'
    second = b'{"metadata":{"request_id":"b","timestamp":"one"}}'
    third = b'{"metadata":{"request_id":"b","timestamp":"two"}}'
    assert policy.http_key(
        "POST", "https://example.test/run", first, headers
    ) == policy.http_key("POST", "https://example.test/run", second, headers)
    assert policy.http_key(
        "POST", "https://example.test/run", first, headers
    ) != policy.http_key("POST", "https://example.test/run", third, headers)


def test_http_query_order_and_default_port_are_normalized() -> None:
    policy = MatchPolicy()
    assert policy.http_key(
        "get", "https://EXAMPLE.test:443/a?b=2&a=1"
    ) == policy.http_key("GET", "https://example.test/a?a=1&b=2")


def test_header_matching_is_opt_in() -> None:
    default = MatchPolicy()
    selected = MatchPolicy(match_headers=("x-model",))
    left = {"x-model": "a"}
    right = {"x-model": "b"}
    assert default.http_key(
        "GET", "https://example.test", headers=left
    ) == default.http_key("GET", "https://example.test", headers=right)
    assert selected.http_key(
        "GET", "https://example.test", headers=left
    ) != selected.http_key("GET", "https://example.test", headers=right)


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(MatchPolicyError):
        MatchPolicy(ignore_body_paths=("timestamp",))


def test_raw_bytes_and_json_object_cannot_share_a_key() -> None:
    import hashlib

    policy = MatchPolicy()
    raw = b"not json"
    fake_json = {"kind": "raw", "sha256": hashlib.sha256(raw).hexdigest()}
    url = "https://example.test/upload"
    assert policy.http_key("POST", url, raw) != policy.http_key("POST", url, fake_json)
