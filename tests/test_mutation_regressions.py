"""Boundary regressions identified by the mutation run."""

import hashlib
import math

import pytest
from test_replay_index import item

from agentrec.canonical import (
    CanonicalValueError,
    canonical_bytes,
    canonical_json,
    decode_canonical,
    decode_special_values,
    encode_special_values,
)
from agentrec.cassette.replay import ReplayIndex, _first_difference, _summary
from agentrec.errors import ReplayMissError
from agentrec.matching import MatchPolicy, MatchPolicyError, _remove_pointer


def test_canonical_wire_encoding_preserves_unicode_and_types():
    assert (
        canonical_json({"é": [1, 1.0, True, None, "x"]})
        == '{"$object":[["é",{"$list":[1,1.0,true,null,"x"]}]]}'
    )
    assert canonical_bytes("é") == b'"\xc3\xa9"'
    assert decode_canonical(canonical_json(float("-inf"))) == float("-inf")


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "{}",
        '{"$float":"bad"}',
        '{"$list":1}',
        '{"$object":1}',
        '{"$object":[1]}',
        '{"$object":[[1,2]]}',
        '{"$object":[["x",1],["x",2]]}',
        '{"$unknown":0}',
        ' {"$list":[]}',
    ],
)
def test_invalid_canonical_tags_fail_explicitly(text):
    with pytest.raises(CanonicalValueError):
        decode_canonical(text)


@pytest.mark.parametrize(
    "value",
    [
        {"$float": []},
        {"$float": "invalid"},
        {"$object": "bad"},
        {"$object": []},
        {"$object": [["x", 1]]},
        {"$object": [["$float"]]},
    ],
)
def test_invalid_storage_tags_fail_explicitly(value):
    with pytest.raises(CanonicalValueError):
        decode_special_values(value)


def test_special_storage_nested_tags_and_literals():
    value = [
        {"x": float("inf")},
        {"$object": [["$float", float("-inf")]]},
        {"$float": "nan"},
        float("nan"),
    ]
    restored = decode_special_values(encode_special_values(value))
    assert restored[:3] == value[:3] and math.isnan(restored[3])
    assert encode_special_values(float("-inf")) == {"$float": "-inf"}
    assert encode_special_values(float("inf")) == {"$float": "inf"}
    assert encode_special_values(float("nan")) == {"$float": "nan"}
    with pytest.raises(CanonicalValueError):
        encode_special_values({1: "bad"})
    with pytest.raises(CanonicalValueError):
        encode_special_values(object())


def test_explicit_pointer_escaping_arrays_missing_and_root():
    assert _remove_pointer({"a/b": {"~key": 1, "keep": 2}}, "/a~1b/~0key") == {
        "a/b": {"keep": 2}
    }
    assert _remove_pointer({"a": [{"b": 1, "c": 2}]}, "/a/0/b") == {"a": [{"c": 2}]}
    assert _remove_pointer({"a": [1, 2]}, "/a/0") == {"a": [2]}
    for pointer in ("/missing/a", "/a/5/x", "/a/no/x", "/a/9", "/a/no"):
        assert _remove_pointer({"a": [1, 2]}, pointer) == {"a": [1, 2]}
    for pointer in ("/", "bad"):
        with pytest.raises(MatchPolicyError):
            _remove_pointer({}, pointer)


def test_policy_identity_and_body_branches_are_exact():
    policy = MatchPolicy(
        ignore_body_paths=("/x",), ignore_query=("ignored",), match_headers=("X-Test",)
    )
    assert policy.as_dict() == {
        "name": "agentrec-default",
        "version": 1,
        "config": {
            "ignore_body_paths": ["/x"],
            "ignore_query": ["ignored"],
            "match_headers": ["X-Test"],
        },
    }
    assert policy._body(None, "") == {"kind": "none"}
    for raw in (b"oops", "oops", b"\xff"):
        content = raw if isinstance(raw, bytes) else raw.encode()
        assert policy._body(raw, "application/json") == {
            "kind": "raw",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    assert policy._body(b'{"x":1,"z":[2]}', "APPLICATION/JSON") == {
        "kind": "json",
        "value": {"z": [2]},
    }
    assert policy._body('{"x":1,"z":[2]}', "application/json") == {
        "kind": "json",
        "value": {"z": [2]},
    }
    assert policy._body([1, 2], "") == {"kind": "json", "value": [1, 2]}
    assert policy.http_key(
        "GET", "http://example.test?ignored=x", headers={"X-Test": "one"}
    ) == policy.http_key(
        "get", "http://EXAMPLE.test:80/?ignored=y", headers={"x-test": "one"}
    )
    assert policy.http_key("GET", "http://example.test", headers={}) != policy.http_key(
        "GET", "http://example.test", headers={"x-test": "one"}
    )
    for field, left, right in [
        ("name", "lookup", "other"),
        ("arguments", {"x": 1}, {"x": 2}),
    ]:
        args = {"name": "lookup", "arguments": {"x": 1}}
        a = dict(args, **{field: left})
        b = dict(args, **{field: right})
        assert policy.tool_key(**a) != policy.tool_key(**b)
    assert MatchPolicy(version=2).tool_key("lookup", {}) != MatchPolicy().tool_key(
        "lookup", {}
    )
    for kwargs in (
        {"name": ""},
        {"version": 0},
        {"version": -1},
        {"ignore_body_paths": ("/",)},
    ):
        with pytest.raises(MatchPolicyError):
            MatchPolicy(**kwargs)
    for url in ("example.test", "http:/missing"):
        with pytest.raises(MatchPolicyError):
            policy.http_key("GET", url)
    with pytest.raises(MatchPolicyError):
        policy.tool_key("", {})


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ({}, {"a": 1}, "/a"),
        ({"a": 1}, {}, "/a"),
        ([1], [1, 2], "/1"),
        ([1, 2], [1], "/1"),
        ([1], [2], "/0"),
        ({"x": [1]}, {"x": [2]}, "/x/0"),
        (1, 2, "/"),
        ([], [], None),
    ],
)
def test_first_difference_reports_actual_path(left, right, expected):
    assert _first_difference(left, right) == expected


def test_replay_summaries_misses_and_order_accounting():
    assert (
        _summary({"method": "POST", "url": "https://example.test"})
        == "POST https://example.test"
    )
    assert _summary({"name": "lookup"}) == "tool lookup"
    assert _summary({}) == "request"
    entries = [item(0, "a" * 64, 0, "one"), item(1, "b" * 64, 0, "two")]
    strict = ReplayIndex(entries, strict_order=True)
    strict.play(entries[0].key, entries[0].request)
    strict.play(entries[1].key, entries[1].request)
    assert strict.unplayed == [] and strict.all_played
    with pytest.raises(ValueError, match="contiguous"):
        ReplayIndex([item(1, "a" * 64, 0, "bad")])
    with pytest.raises(ReplayMissError, match="no similar recorded request"):
        ReplayIndex(entries).play("c" * 64, {"name": "missing", "arguments": {}})
    with pytest.raises(ReplayMissError, match="seq 0 first differing path"):
        ReplayIndex(entries).play("c" * 64, entries[0].request)


@pytest.mark.parametrize(
    "method,url,body,headers",
    [
        (
            "GET",
            "https://example.test:8443/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "http://example.test:8443/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://other.test:8443/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://example.test:8444/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://example.test:8443/two?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://example.test:8443/one?a=2",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://example.test:8443/one?a=1",
            b'{"x":2}',
            {"content-type": "application/json", "x-model": "one"},
        ),
        (
            "POST",
            "https://example.test:8443/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "two"},
        ),
    ],
)
def test_every_semantic_http_component_changes_key(method, url, body, headers):
    policy = MatchPolicy(match_headers=("x-model",))
    baseline = policy.http_key(
        "POST",
        "https://example.test:8443/one?a=1",
        b'{"x":1}',
        {"content-type": "application/json", "x-model": "one"},
    )
    assert policy.http_key(method, url, body, headers) != baseline


def test_json_whitespace_is_ignored_and_raw_bytes_are_exact():
    policy = MatchPolicy()
    url = "https://example.test"
    assert policy.http_key(
        "POST", url, b'{"a":1,"b":2}', {"content-type": "application/json"}
    ) == policy.http_key(
        "POST", url, b'{ "b": 2, "a": 1 }', {"content-type": "application/json"}
    )
    assert policy.http_key("POST", url, b"a") != policy.http_key("POST", url, b"b")
    assert policy.http_key("POST", url, "a") != policy.http_key("POST", url, "b")
    assert policy.http_key(
        "POST", url, b'{"a":1}', {"content-type": "application/json"}
    ) != policy.http_key("POST", url, b'{"a":1}')


def test_version_one_match_keys_are_wire_stable():
    # Golden digests protect persisted keys against unversioned policy changes.
    policy = MatchPolicy(match_headers=("x-model",))
    assert (
        policy.http_key(
            "POST",
            "https://example.test:8443/one?a=1",
            b'{"x":1}',
            {"content-type": "application/json", "x-model": "one"},
        )
        == "e76940970f36cceb56e6bd4913be52568e094181b34d78f0f213cac1e4aef8f3"
    )
    assert (
        policy.tool_key("lookup", {"x": 1})
        == "1343abd8f4a515fbc53092ca44ce423a5e54ef7ed25786401ba57fc01edd0fda"
    )
