"""Request normalization used before content hashing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

UNSTABLE_FIELD_NAMES = {
    "created_at",
    "random_id",
    "request_id",
    "run_id",
    "span_id",
    "timestamp",
    "trace_id",
    "updated_at",
}


def normalize_request(data: dict[str, Any]) -> dict[str, Any]:
    """Return a stable JSON-compatible request structure."""

    normalized = _normalize_value(data)
    if not isinstance(normalized, dict):
        msg = "normalize_request expects a dictionary input"
        raise TypeError(msg)
    return normalized


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_value(value[key])
            for key in sorted(value, key=str)
            if str(key) not in UNSTABLE_FIELD_NAMES
        }

    if isinstance(value, list | tuple):
        return [_normalize_value(item) for item in value]

    if isinstance(value, str | int | float | bool) or value is None:
        return value

    if hasattr(value, "model_dump"):
        return _normalize_value(value.model_dump(mode="json"))

    return str(value)
