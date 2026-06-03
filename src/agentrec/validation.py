"""Cassette validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentrec.models import CachedInteraction
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
            run = store.read_metadata()
            run_id = run.run_id
            task = run.task
        except Exception as exc:  # noqa: BLE001 - validation should collect failures.
            errors.append(f"Invalid metadata.json: {exc}")

    if store.trace_path.is_file():
        try:
            step_count = len(store.read_steps())
        except Exception as exc:  # noqa: BLE001 - validation should collect failures.
            errors.append(f"Invalid trace.jsonl: {exc}")

    if store.final_output_path.exists():
        try:
            store.read_final_output()
            has_final_output = True
        except Exception as exc:  # noqa: BLE001 - validation should collect failures.
            errors.append(f"Invalid final_output.txt: {exc}")

    if store.responses_path.is_dir():
        response_files = sorted(store.responses_path.glob("*.json"))
        response_file_count = len(response_files)
        for response_file in response_files:
            try:
                data = json.loads(response_file.read_text(encoding="utf-8"))
                CachedInteraction.model_validate(data)
            except Exception as exc:  # noqa: BLE001 - validation should collect failures.
                errors.append(f"Invalid response file {response_file.name}: {exc}")

    return {
        "ok": not errors,
        "run_path": str(path),
        "run_id": run_id,
        "task": task,
        "step_count": step_count,
        "response_file_count": response_file_count,
        "has_final_output": has_final_output,
        "errors": errors,
    }
