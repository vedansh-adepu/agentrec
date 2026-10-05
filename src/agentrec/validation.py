"""Cassette validation helpers."""

from __future__ import annotations

import base64
import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from agentrec.canonical import decode_special_values
from agentrec.cassette.replay import ReplayIndex
from agentrec.cassette.store import CassetteStore as V2CassetteStore
from agentrec.matching import MatchPolicy, MatchPolicyError
from agentrec.models import CASSETTE_SCHEMA_VERSION, CachedInteraction
from agentrec.redaction import privacy_findings
from agentrec.store import CassetteStore


def validate_cassette(run_path: str | Path) -> dict[str, Any]:
    """Validate a cassette folder and return a JSON-serializable summary."""

    path = Path(run_path)
    store = CassetteStore(path)
    errors: list[str] = []
    run_id: str | None = None
    task: str | None = None
    step_count = 0
    response_file_count = 0
    has_final_output = False
    schema_version: str | None = None

    if not path.exists():
        errors.append(f"Missing cassette path: {path}")
    elif not path.is_dir():
        errors.append(f"Cassette path is not a directory: {path}")

    if not store.metadata_path.is_file():
        errors.append(f"Missing metadata.json: {store.metadata_path}")
    if not store.trace_path.is_file():
        errors.append(f"Missing trace.jsonl: {store.trace_path}")
    if not store.responses_path.is_dir():
        errors.append(f"Missing responses directory: {store.responses_path}")
    if not store.artifacts_path.is_dir():
        errors.append(f"Missing artifacts directory: {store.artifacts_path}")

    if store.metadata_path.is_file():
        try:
            metadata = json.loads(store.metadata_path.read_text(encoding="utf-8"))
            raw_schema_version = metadata.get("schema_version")
            if raw_schema_version is None:
                errors.append("Missing metadata schema_version")
            elif raw_schema_version != CASSETTE_SCHEMA_VERSION:
                errors.append(
                    f"Unsupported metadata schema_version {raw_schema_version!r}; "
                    f"expected {CASSETTE_SCHEMA_VERSION!r}",
                )
            else:
                schema_version = raw_schema_version
            run = store.read_metadata()
            run_id = run.run_id
            task = run.task
        except Exception as exc:
            errors.append(f"Invalid metadata.json: {exc}")

    if store.trace_path.is_file():
        try:
            steps = store.read_steps()
            step_count = len(steps)
            expected_indexes = list(range(step_count))
            actual_indexes = [step.index for step in steps]
            if actual_indexes != expected_indexes:
                errors.append(
                    "Invalid trace.jsonl: step indexes must be ordered from 0 "
                    f"without gaps; got {actual_indexes}",
                )
        except Exception as exc:
            errors.append(f"Invalid trace.jsonl: {exc}")

    if store.final_output_path.exists():
        try:
            store.read_final_output()
            has_final_output = True
        except Exception as exc:
            errors.append(f"Invalid final_output.txt: {exc}")

    if store.responses_path.is_dir():
        response_files = sorted(store.responses_path.glob("*.json"))
        response_file_count = len(response_files)
        for response_file in response_files:
            try:
                data = json.loads(response_file.read_text(encoding="utf-8"))
                interaction = CachedInteraction.model_validate(data)
                expected_suffix = f"_{interaction.kind}.json"
                if not response_file.name.endswith(expected_suffix):
                    errors.append(
                        f"Invalid response file {response_file.name}: "
                        "filename kind does not match payload kind "
                        f"{interaction.kind!r}",
                    )
                expected_name = f"{interaction.request_hash}_{interaction.kind}.json"
                if response_file.name != expected_name:
                    errors.append(
                        f"Invalid response file {response_file.name}: "
                        f"expected filename {expected_name}",
                    )
            except Exception as exc:
                errors.append(f"Invalid response file {response_file.name}: {exc}")

    return {
        "ok": not errors,
        "run_path": str(path),
        "run_id": run_id,
        "task": task,
        "schema_version": schema_version,
        "step_count": step_count,
        "response_file_count": response_file_count,
        "has_final_output": has_final_output,
        "errors": errors,
    }


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
        metadata, interactions = store.load()
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
            raw = (path / "interactions.jsonl").read_bytes()
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
