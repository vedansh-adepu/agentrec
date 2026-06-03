"""Minimal cassette diff engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentrec.errors import CassetteNotFoundError
from agentrec.models import RunRecord, Step
from agentrec.store import CassetteStore


def diff_cassettes(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    """Compare two cassette runs and return a JSON-serializable summary."""

    left_store = CassetteStore(left_path)
    right_store = CassetteStore(right_path)
    left_store.validate()
    right_store.validate()

    left_run = left_store.read_metadata()
    right_run = right_store.read_metadata()
    left_steps = left_store.read_steps()
    right_steps = right_store.read_steps()
    left_final_output = _read_final_output(left_store, left_run)
    right_final_output = _read_final_output(right_store, right_run)

    left_sequence = _step_sequence(left_steps)
    right_sequence = _step_sequence(right_steps)
    left_names = _step_names(left_steps)
    right_names = _step_names(right_steps)
    final_output_changed = left_final_output != right_final_output
    step_count_changed = len(left_steps) != len(right_steps)
    step_sequence_changed = left_sequence != right_sequence
    step_names_changed = left_names != right_names
    run_id_changed = left_run.run_id != right_run.run_id
    task_changed = left_run.task != right_run.task
    left_total_latency = _total_latency_ms(left_steps)
    right_total_latency = _total_latency_ms(right_steps)
    left_total_cost = _total_cost_usd(left_steps)
    right_total_cost = _total_cost_usd(right_steps)
    cost_delta = right_total_cost - left_total_cost

    changed = any(
        (
            run_id_changed,
            task_changed,
            final_output_changed,
            step_count_changed,
            step_sequence_changed,
            step_names_changed,
            cost_delta != 0,
        ),
    )

    return {
        "left_run_id": left_run.run_id,
        "right_run_id": right_run.run_id,
        "run_id_changed": run_id_changed,
        "left_task": left_run.task,
        "right_task": right_run.task,
        "task_changed": task_changed,
        "left_final_output": left_final_output,
        "right_final_output": right_final_output,
        "final_output_changed": final_output_changed,
        "left_step_count": len(left_steps),
        "right_step_count": len(right_steps),
        "step_count_changed": step_count_changed,
        "left_step_sequence": left_sequence,
        "right_step_sequence": right_sequence,
        "step_sequence_changed": step_sequence_changed,
        "left_step_names": left_names,
        "right_step_names": right_names,
        "step_names_changed": step_names_changed,
        "left_total_latency_ms": left_total_latency,
        "right_total_latency_ms": right_total_latency,
        "latency_delta_ms": right_total_latency - left_total_latency,
        "left_total_cost_usd": left_total_cost,
        "right_total_cost_usd": right_total_cost,
        "cost_delta_usd": cost_delta,
        "changed": changed,
    }


def _read_final_output(store: CassetteStore, run: RunRecord) -> str | None:
    try:
        return store.read_final_output()
    except CassetteNotFoundError:
        return run.final_output


def _step_sequence(steps: list[Step]) -> list[str]:
    return [f"{step.kind}:{step.name}" for step in steps]


def _step_names(steps: list[Step]) -> list[str]:
    return [step.name for step in steps]


def _total_latency_ms(steps: list[Step]) -> float:
    return sum(step.latency_ms or 0.0 for step in steps)


def _total_cost_usd(steps: list[Step]) -> float:
    return sum(step.usage.cost_usd for step in steps if step.usage is not None)
