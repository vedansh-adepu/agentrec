"""Content hashing for normalized requests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agentrec._legacy.normalizer import normalize_request


def hash_request(data: dict[str, Any]) -> str:
    """Return a SHA-256 hex digest for a normalized request."""

    normalized = normalize_request(data)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
