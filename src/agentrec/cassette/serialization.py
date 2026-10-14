"""One byte serializer for schema-v2 interaction digests and writes."""

from __future__ import annotations

import json
from typing import Any

from .model import Interaction


def _sorted_record(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sorted_record(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted_record(item) for item in value]
    return value


def interaction_bytes(item: Interaction) -> bytes:
    """Sort envelope fields while retaining tool-result dictionary insertion order."""
    record = item.model_dump(mode="json")
    ordered = _sorted_record(record)
    if item.kind == "tool" and item.response is not None:
        ordered["response"]["result"] = record["response"]["result"]
    return (
        json.dumps(ordered, separators=(",", ":"), allow_nan=False).encode("utf-8")
        + b"\n"
    )
