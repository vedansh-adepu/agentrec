"""Strict, versioned canonical JSON encoding for match keys."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import TypeAlias

from agentrec.errors import AgentRecError

JsonValue: TypeAlias = (
    "bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None"
)


class CanonicalValueError(AgentRecError, ValueError):
    """Raised when a value cannot be represented by canonical JSON."""

    code = "AR301"
    hint = "Use JSON value types with string object keys."


def _tag(value: object) -> object:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"$float": "nan"}
        if math.isinf(value):
            return {"$float": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, list):
        return {"$list": [_tag(item) for item in value]}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalValueError("canonical object keys must be strings")
        return {"$object": [[key, _tag(value[key])] for key in sorted(value)]}
    raise CanonicalValueError(
        f"unsupported canonical value type: {type(value).__name__}"
    )


def _untag(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if not isinstance(value, dict) or len(value) != 1:
        raise CanonicalValueError("invalid canonical tag")
    if "$float" in value:
        label = value["$float"]
        if label not in ("nan", "inf", "-inf"):
            raise CanonicalValueError("invalid float tag")
        return {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}[label]
    if "$list" in value:
        items = value["$list"]
        if not isinstance(items, list):
            raise CanonicalValueError("invalid list tag")
        return [_untag(item) for item in items]
    if "$object" in value:
        pairs = value["$object"]
        if not isinstance(pairs, list):
            raise CanonicalValueError("invalid object tag")
        result: dict[str, JsonValue] = {}
        for pair in pairs:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not isinstance(pair[0], str)
            ):
                raise CanonicalValueError("invalid object entry")
            if pair[0] in result:
                raise CanonicalValueError("duplicate object key")
            result[pair[0]] = _untag(pair[1])
        return result
    raise CanonicalValueError("unknown canonical tag")


def canonical_json(value: JsonValue) -> str:
    """Encode supported JSON values with stable order and tagged special floats."""
    tagged = _tag(value)
    try:
        return json.dumps(
            tagged, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
    except ValueError as exc:
        raise CanonicalValueError(
            "canonical value exceeds JSON serializer limits"
        ) from exc


def canonical_bytes(value: JsonValue) -> bytes:
    """Return the UTF-8 bytes used for deterministic SHA-256 keys."""
    return canonical_json(value).encode("utf-8")


def canonical_sha256(value: JsonValue) -> str:
    """Return a SHA-256 digest of the canonical byte encoding."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def decode_canonical(text: str) -> JsonValue:
    """Decode a canonical string, rejecting malformed or noncanonical input."""
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise CanonicalValueError("invalid canonical JSON") from exc
    result = _untag(parsed)
    if canonical_json(result) != text:
        raise CanonicalValueError("noncanonical JSON encoding")
    return result


def encode_special_values(value: JsonValue) -> JsonValue:
    """Tag non-finite floats for JSON storage without colliding with user dicts."""
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return {"$float": "nan"}
        if math.isinf(value):
            return {"$float": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, list):
        return [encode_special_values(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalValueError("stored object keys must be strings")
        encoded = {key: encode_special_values(item) for key, item in value.items()}
        if len(encoded) == 1 and next(iter(encoded)) in {"$float", "$object"}:
            key = next(iter(encoded))
            return {"$object": [[key, encoded[key]]]}
        return encoded
    raise CanonicalValueError(f"unsupported stored value type: {type(value).__name__}")


def decode_special_values(value: JsonValue) -> JsonValue:
    """Restore tagged floats and escaped literal dictionaries from storage."""
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, list):
        return [decode_special_values(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalValueError("stored object keys must be strings")
        if len(value) == 1 and "$float" in value:
            label = value["$float"]
            if label not in ("nan", "inf", "-inf"):
                raise CanonicalValueError("invalid stored float tag")
            return {
                "nan": float("nan"),
                "inf": float("inf"),
                "-inf": float("-inf"),
            }[label]
        if len(value) == 1 and "$object" in value:
            pairs = value["$object"]
            if not isinstance(pairs, list) or len(pairs) != 1:
                raise CanonicalValueError("invalid stored object escape")
            pair = pairs[0]
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or pair[0] not in ("$float", "$object")
            ):
                raise CanonicalValueError("invalid stored object escape")
            return {pair[0]: decode_special_values(pair[1])}
        return {key: decode_special_values(item) for key, item in value.items()}
    raise CanonicalValueError("invalid stored value type")
