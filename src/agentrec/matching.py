"""Explicit, versioned request matching for HTTP and tool interactions."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

from agentrec.errors import AgentRecError

from .canonical import JsonValue, canonical_sha256


class MatchPolicyError(AgentRecError, ValueError):
    """Raised for an invalid or unsupported matching policy."""

    code = "AR302"
    hint = "Check the URL, policy version, and explicit JSON-pointer paths."


def _remove_pointer(value: JsonValue, pointer: str) -> JsonValue:
    if not pointer.startswith("/") or pointer == "/":
        raise MatchPolicyError(f"invalid JSON pointer: {pointer!r}")
    parts = [
        part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")
    ]
    current: Any = value
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current.get(part)
        elif (
            isinstance(current, list) and part.isdecimal() and int(part) < len(current)
        ):
            current = current[int(part)]
        else:
            return value
    last = parts[-1]
    if isinstance(current, dict):
        current.pop(last, None)
    elif isinstance(current, list) and last.isdecimal() and int(last) < len(current):
        current.pop(int(last))
    return value


@dataclass(frozen=True)
class MatchPolicy:
    """Define exactly which request fields contribute to versioned match keys."""

    name: str = "agentrec-default"
    version: int = 1
    ignore_body_paths: tuple[str, ...] = ()
    ignore_query: tuple[str, ...] = ()
    match_headers: tuple[str, ...] = ()
    _ignored_query: frozenset[str] = field(init=False, repr=False)
    _matched_headers: frozenset[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name or self.version < 1:
            raise MatchPolicyError("policy name must be nonempty and version positive")
        for pointer in self.ignore_body_paths:
            if not pointer.startswith("/") or pointer == "/":
                raise MatchPolicyError(f"invalid JSON pointer: {pointer!r}")
        object.__setattr__(self, "_ignored_query", frozenset(self.ignore_query))
        object.__setattr__(
            self,
            "_matched_headers",
            frozenset(name.lower() for name in self.match_headers),
        )

    def as_dict(self) -> dict[str, JsonValue]:
        """Return the persisted policy identity and configuration."""
        return {
            "name": self.name,
            "version": self.version,
            "config": {
                "ignore_body_paths": list(self.ignore_body_paths),
                "ignore_query": list(self.ignore_query),
                "match_headers": list(self.match_headers),
            },
        }

    def _body(self, body: JsonValue | bytes | None, content_type: str) -> JsonValue:
        if body is None:
            return {"kind": "none"}
        parsed: JsonValue
        if isinstance(body, bytes):
            if "json" in content_type.lower():
                try:
                    parsed = cast(JsonValue, json.loads(body))
                except (UnicodeDecodeError, ValueError):
                    return {"kind": "raw", "sha256": hashlib.sha256(body).hexdigest()}
            else:
                return {"kind": "raw", "sha256": hashlib.sha256(body).hexdigest()}
        elif isinstance(body, str):
            if "json" in content_type.lower():
                try:
                    parsed = cast(JsonValue, json.loads(body))
                except ValueError:
                    return {
                        "kind": "raw",
                        "sha256": hashlib.sha256(body.encode()).hexdigest(),
                    }
            else:
                return {
                    "kind": "raw",
                    "sha256": hashlib.sha256(body.encode()).hexdigest(),
                }
        else:
            parsed = body
        if isinstance(parsed, dict | list):
            parsed = copy.deepcopy(parsed)
            for pointer in self.ignore_body_paths:
                parsed = _remove_pointer(parsed, pointer)
        return {"kind": "json", "value": parsed}

    def http_key(
        self,
        method: str,
        url: str,
        body: JsonValue | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Hash the method, URL components, query, selected headers, and body."""
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.hostname:
            raise MatchPolicyError("HTTP URL must include a scheme and host")
        selected = {key.lower(): value for key, value in (headers or {}).items()}
        query = sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in self._ignored_query
        )
        payload: JsonValue = {
            "policy": self.as_dict(),
            "kind": "http",
            "method": method.upper(),
            "scheme": parsed.scheme.lower(),
            "host": parsed.hostname.lower(),
            "port": parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
            "path": parsed.path or "/",
            "query": [[key, value] for key, value in query],
            "headers": {
                key: selected[key]
                for key in sorted(self._matched_headers)
                if key in selected
            },
            "body": self._body(body, selected.get("content-type", "")),
        }
        return canonical_sha256(payload)

    def tool_key(self, name: str, arguments: dict[str, JsonValue]) -> str:
        """Hash a tool name and its canonical argument mapping."""
        if not name:
            raise MatchPolicyError("tool name must be nonempty")
        return canonical_sha256(
            {
                "policy": self.as_dict(),
                "kind": "tool",
                "name": name,
                "arguments": arguments,
            }
        )
