"""Pre-persistence redaction and privacy scanning for cassette values."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .cassette.model import CassetteMetadata, ErrorRecord, Interaction
from .cassette.store import CassetteStore

REDACTION_POLICY_VERSION = 1
DEFAULT_HEADERS = frozenset(
    {
        "authorization",
        "x-api-key",
        "api-key",
        "openai-organization",
        "cookie",
        "set-cookie",
    }
)
DEFAULT_QUERY_PATTERN = re.compile(r"api_key|key|token|secret", re.IGNORECASE)
BUILTIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{12,}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{8,}"),
    "jwt": re.compile(
        r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])"
    ),
    "bearer": re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{8,}", re.IGNORECASE),
    "pem_private_key": re.compile(
        r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
        r"[\s\S]*?-----END (?:[A-Z ]+ )?PRIVATE KEY-----"
    ),
}
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9_+/-]{24,}")


class Redactor:
    """Redact configured headers, query values, and secret-like strings."""

    def __init__(
        self,
        *,
        header_names: set[str] | None = None,
        query_pattern: re.Pattern[str] = DEFAULT_QUERY_PATTERN,
        custom_patterns: Mapping[str, str | re.Pattern[str]] | None = None,
        redact_email: bool = False,
        entropy_threshold: float | None = None,
        before_record_request: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        before_record_response: Callable[[dict[str, Any]], dict[str, Any]]
        | None = None,
        before_record_tool: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        """Configure extra rules and in-memory hooks before any persistence."""
        self.header_names = frozenset(
            name.lower() for name in (header_names or DEFAULT_HEADERS)
        )
        self.query_pattern = query_pattern
        self.patterns = dict(BUILTIN_PATTERNS)
        for name, pattern in (custom_patterns or {}).items():
            self.patterns[name] = (
                re.compile(pattern) if isinstance(pattern, str) else pattern
            )
        if redact_email:
            self.patterns["email"] = EMAIL_PATTERN
        self.entropy_threshold = entropy_threshold
        self.before_record_request = before_record_request
        self.before_record_response = before_record_response
        self.before_record_tool = before_record_tool

    def redact_text(self, value: str) -> str:
        """Replace every configured secret pattern in a single string."""
        for name, pattern in self.patterns.items():
            value = pattern.sub(f"[REDACTED:{name}]", value)
        threshold = self.entropy_threshold
        if threshold is not None:

            def replace(match: re.Match[str]) -> str:
                candidate = match.group()
                counts = {char: candidate.count(char) for char in set(candidate)}
                entropy = -sum(
                    (count / len(candidate)) * math.log2(count / len(candidate))
                    for count in counts.values()
                )
                return "[REDACTED:entropy]" if entropy >= threshold else candidate

            value = ENTROPY_CANDIDATE.sub(replace, value)
        return value

    def redact_value(self, value: Any) -> Any:
        """Recursively scan stored strings without coercing unknown value types."""
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, list):
            return [self.redact_value(item) for item in value]
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                replacement = self.redact_text(key)
                if replacement in result:
                    raise ValueError("redaction would collapse distinct object keys")
                result[replacement] = self.redact_value(item)
            return result
        return value

    def redact_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        """Redact sensitive header values by case-insensitive name."""
        return {
            name: (
                "[REDACTED:header]"
                if name.lower() in self.header_names
                else self.redact_text(value)
            )
            for name, value in headers.items()
        }

    def redact_url(self, url: str) -> str:
        """Redact sensitive query values while retaining URL structure."""
        parsed = urlsplit(url)
        query = [
            (
                name,
                "[REDACTED:query]"
                if self.query_pattern.search(name)
                else self.redact_text(value),
            )
            for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query),
                parsed.fragment,
            )
        )

    def redact_request(self, request: dict[str, Any], *, kind: str) -> dict[str, Any]:
        """Apply a request or tool hook, then redact before recording."""
        value = dict(request)
        hook = self.before_record_tool if kind == "tool" else self.before_record_request
        if hook is not None:
            value = hook(value)
        value = self.redact_value(value)
        if kind == "http":
            if "url" in value:
                value["url"] = self.redact_url(value["url"])
            if "headers" in value:
                value["headers"] = self.redact_headers(value["headers"])
        return cast(dict[str, Any], value)

    def redact_response(self, response: dict[str, Any], *, kind: str) -> dict[str, Any]:
        """Apply a response or tool hook, then redact before recording."""
        value = dict(response)
        hook = (
            self.before_record_tool if kind == "tool" else self.before_record_response
        )
        if hook is not None:
            value = hook(value)
        value = self.redact_value(value)
        if kind == "http" and "headers" in value:
            value["headers"] = self.redact_headers(value["headers"])
        return cast(dict[str, Any], value)


def privacy_findings(
    interactions: list[Interaction], metadata: CassetteMetadata | None = None
) -> list[str]:
    """Return paths where built-in secret patterns remain in parsed records."""
    findings: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, str):
            for name, pattern in BUILTIN_PATTERNS.items():
                if pattern.search(value):
                    findings.append(f"{path}: {name}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}/{index}")
        elif isinstance(value, dict):
            for key, item in value.items():
                visit(key, f"{path}/<object-key>")
                safe_key = Redactor().redact_text(key)
                visit(item, f"{path}/{safe_key}")

    if metadata and metadata.error:
        visit(metadata.error.message, "/cassette/error")
    for interaction in interactions:
        visit(interaction.request, f"/interactions/{interaction.seq}/request")
        visit(interaction.response, f"/interactions/{interaction.seq}/response")
        if interaction.error:
            visit(interaction.error.message, f"/interactions/{interaction.seq}/error")
    return findings


def scrub(path: str | Path, redactor: Redactor | None = None) -> int:
    """Atomically re-redact an owned cassette and return changed step count."""
    active = redactor or Redactor()
    store = CassetteStore(path)
    store.require_owned()
    metadata, interactions = store.load()
    changed = 0
    updated: list[Interaction] = []
    for item in interactions:
        request = active.redact_request(item.request, kind=item.kind)
        response = (
            active.redact_response(item.response, kind=item.kind)
            if item.response is not None
            else None
        )
        error = (
            ErrorRecord(
                type=item.error.type, message=active.redact_text(item.error.message)
            )
            if item.error
            else None
        )
        if request != item.request or response != item.response or error != item.error:
            changed += 1
        updated.append(
            item.model_copy(
                update={
                    "request": request,
                    "response": response,
                    "error": error,
                    "key_inputs_redacted": item.key_inputs_redacted
                    or request != item.request,
                }
            )
        )
    data = b"".join(
        json.dumps(
            item.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        + b"\n"
        for item in updated
    )
    metadata_error = (
        ErrorRecord(
            type=metadata.error.type,
            message=active.redact_text(metadata.error.message),
        )
        if metadata.error
        else None
    )
    metadata = metadata.model_copy(
        update={
            "redaction_policy_version": REDACTION_POLICY_VERSION,
            "content_sha256": hashlib.sha256(data).hexdigest(),
            "finalized_at": datetime.now(UTC),
            "error": metadata_error,
        }
    )
    store.save(metadata, updated, replace=True)
    return changed
