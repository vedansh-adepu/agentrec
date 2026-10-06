"""Semantic regressions from a complete canonical mutant review."""

import math
import sys

import pytest

from agentrec.canonical import (
    CanonicalValueError,
    canonical_bytes,
    canonical_json,
    decode_canonical,
    decode_special_values,
    encode_special_values,
)


@pytest.mark.parametrize(
    "text", ['["$float"]', '["$object"]', '{"$object":[["x"]]}', '{"$object":[[[],1]]}']
)
def test_malformed_tag_containers_raise_documented_error(text: str) -> None:
    with pytest.raises(CanonicalValueError) as caught:
        decode_canonical(text)
    assert caught.value.code == "AR301"


@pytest.mark.parametrize("label", [None, True, 1, 1.0, [], {}, "NaN", "infinity"])
def test_wrong_float_tag_value_types_are_rejected(label) -> None:
    import json

    for decode, value in (
        (decode_special_values, {"$float": label}),
        (decode_canonical, json.dumps({"$float": label})),
    ):
        with pytest.raises(CanonicalValueError):
            decode(value)


def test_unknown_stored_value_preserves_error_type_and_code() -> None:
    with pytest.raises(CanonicalValueError) as caught:
        decode_special_values(object())
    assert caught.value.code == "AR301"


@pytest.mark.parametrize("key", [1, True, None, ("x",)])
def test_non_string_keys_are_rejected_by_all_codecs(key) -> None:
    for codec in (canonical_json, encode_special_values, decode_special_values):
        with pytest.raises(CanonicalValueError):
            codec({key: "value"})


def test_nested_tag_like_user_data_is_preserved_without_accidental_decode() -> None:
    data = {
        "$float": "nan",
        "keep": [
            {"$float": "inf"},
            {"$object": [["$float", "inf"]]},
            {"$list": [1, 2]},
            {"$float": {"$float": "nan"}},
        ],
    }
    assert decode_canonical(canonical_json(data)) == data
    assert decode_special_values(encode_special_values(data)) == data
    tagged = {"nested": [float("inf"), float("-inf"), {"value": float("nan")}]}
    restored = decode_special_values(encode_special_values(tagged))["nested"]
    assert restored[0] == float("inf") and restored[1] == float("-inf")
    assert math.isnan(restored[2]["value"])


def test_bool_integer_and_signed_zero_keep_distinct_types_and_keys() -> None:
    assert canonical_bytes(True) != canonical_bytes(1)
    assert canonical_bytes(False) != canonical_bytes(0)
    assert canonical_bytes(-0.0) != canonical_bytes(0.0)
    assert type(decode_canonical(canonical_json(True))) is bool
    assert type(decode_canonical(canonical_json(1))) is int
    zero = decode_canonical(canonical_json(-0.0))
    assert math.copysign(1.0, zero) == -1.0


def test_large_integers_roundtrip_without_float_conversion() -> None:
    value = 2**4096 + 1
    for integer in (value, -value):
        restored = decode_canonical(canonical_json(integer))
        assert type(restored) is int and restored == integer
        assert decode_special_values(encode_special_values(integer)) == integer


def test_integer_beyond_runtime_json_limit_has_documented_error() -> None:
    limit = sys.get_int_max_str_digits()
    if not limit or limit > 10000:
        pytest.skip(
            "The runtime integer digit limit is disabled or exceeds this bounded test."
        )
    with pytest.raises(CanonicalValueError):
        canonical_json(10 ** (limit + 1))
