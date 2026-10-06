"""Cassette validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentrec._legacy.models import CASSETTE_SCHEMA_VERSION, CachedInteraction
from agentrec._legacy.store import CassetteStore


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
