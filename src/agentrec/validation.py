"""Structural, integrity, replayability, and privacy checks for schema v2."""

from __future__ import annotations

import base64
import hashlib
from enum import StrEnum
from pathlib import Path
from typing import Any

from agentrec.canonical import decode_special_values
from agentrec.cassette.model import CassetteMetadata, Interaction
from agentrec.cassette.replay import ReplayIndex
from agentrec.cassette.store import CassetteStore as V2CassetteStore
from agentrec.matching import MatchPolicy, MatchPolicyError
from agentrec.redaction import privacy_findings


class ValidationLevel(StrEnum):
    """Choose cumulative structural, integrity, replayability, or privacy checks."""

    STRUCTURAL = "structural"
    INTEGRITY = "integrity"
    REPLAYABLE = "replayable"
    PRIVACY = "privacy"


def _policy_from_record(record: Any) -> MatchPolicy:
    config = record.config
    allowed = {"ignore_body_paths", "ignore_query", "match_headers"}
    if set(config) - allowed:
        raise MatchPolicyError("unknown match-policy configuration field")
    return MatchPolicy(
        name=record.name,
        version=record.version,
        ignore_body_paths=tuple(config.get("ignore_body_paths", [])),
        ignore_query=tuple(config.get("ignore_query", [])),
        match_headers=tuple(config.get("match_headers", [])),
    )


def _stored_key(policy: MatchPolicy, interaction: Any) -> str:
    request = interaction.request
    if interaction.kind == "tool":
        arguments = decode_special_values(request["arguments"])
        if not isinstance(arguments, dict):
            raise ValueError("stored tool arguments must be a mapping")
        return policy.tool_key(request["name"], arguments)
    body = request.get("body", "")
    if request.get("body_encoding") == "base64":
        raw = base64.b64decode(body, validate=True)
    elif request.get("body_encoding", "text") == "text":
        raw = str(body).encode("utf-8")
    else:
        raise ValueError("unsupported stored body encoding")
    return policy.http_key(
        request["method"], request["url"], raw, request.get("headers", {})
    )


def validate_v2_cassette(
    run_path: str | Path,
    *,
    level: ValidationLevel | str = ValidationLevel.PRIVACY,
    allow_failed: bool = False,
    _loaded: tuple[CassetteMetadata, list[Interaction], bytes] | None = None,
) -> dict[str, Any]:
    """Validate schema-v2 structure, integrity, replayability, and privacy."""
    requested = ValidationLevel(level)
    errors: list[str] = []
    warnings: list[str] = []
    count = 0
    unverifiable = 0
    path = Path(run_path)
    try:
        store = V2CassetteStore(path)
        metadata, interactions, raw = _loaded or store._load_snapshot()
        count = len(interactions)
        if [item.seq for item in interactions] != list(range(count)):
            errors.append("interaction seq values must be contiguous from 0")
    except Exception as exc:
        errors.append(f"structural: {exc}")
        return {
            "ok": False,
            "level": requested.value,
            "run_path": str(path),
            "interaction_count": count,
            "unverifiable_key_count": unverifiable,
            "warnings": warnings,
            "errors": errors,
        }

    if requested is not ValidationLevel.STRUCTURAL:
        try:
            digest = hashlib.sha256(raw).hexdigest()
            if digest != metadata.content_sha256:
                errors.append("content_sha256 does not match interactions.jsonl")
            if metadata.interaction_count != count:
                errors.append("interaction_count does not match interactions.jsonl")
            ReplayIndex(interactions)
            policy = _policy_from_record(metadata.match_policy)
            for item in interactions:
                if item.key_inputs_redacted:
                    unverifiable += 1
                    continue
                try:
                    computed = _stored_key(policy, item)
                except (KeyError, TypeError, ValueError) as exc:
                    errors.append(f"seq {item.seq} invalid stored request: {exc}")
                    continue
                if computed != item.key:
                    errors.append(f"seq {item.seq} key does not match stored request")
            if unverifiable:
                warnings.append(
                    f"{unverifiable} key(s) cannot be recomputed from redacted input"
                )
        except Exception as exc:
            errors.append(f"integrity: {exc}")

    if requested in {ValidationLevel.REPLAYABLE, ValidationLevel.PRIVACY}:
        if metadata.status != "complete" and not (
            allow_failed and metadata.status == "failed"
        ):
            errors.append(f"cassette status {metadata.status!r} is not replayable")
        for item in interactions:
            if (item.response is None) == (item.error is None):
                errors.append(f"seq {item.seq} requires exactly one outcome")

    if requested is ValidationLevel.PRIVACY:
        errors.extend(privacy_findings(interactions, metadata))

    return {
        "ok": not errors,
        "level": requested.value,
        "run_path": str(path),
        "interaction_count": count,
        "unverifiable_key_count": unverifiable,
        "warnings": warnings,
        "errors": errors,
    }
