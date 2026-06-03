"""Command line interface for agentrec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from agentrec.diff import diff_cassettes
from agentrec.errors import CassetteError, ReplayMissError
from agentrec.examples import record_math_flow, replay_math_flow
from agentrec.models import RunRecord, Step
from agentrec.store import CassetteStore

app = typer.Typer(help="Record and replay offline agentrec examples.")


@app.command()
def record(
    run_path: Path = typer.Option(..., "--run-path", help="Path to write the cassette."),
    expression: str = typer.Option("2+3", "--expression", help="Math expression to record."),
) -> None:
    """Record the offline math flow."""

    summary = record_math_flow(run_path, expression)
    typer.echo("Recorded math flow.")
    _print_summary(summary)


@app.command()
def replay(
    run_path: Path = typer.Option(..., "--run-path", help="Path to read the cassette."),
    expression: str = typer.Option("2+3", "--expression", help="Math expression to replay."),
) -> None:
    """Replay the offline math flow."""

    try:
        summary = replay_math_flow(run_path, expression)
    except ReplayMissError as exc:
        typer.secho(f"Replay miss: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo("Replayed math flow.")
    _print_summary(summary)


@app.command()
def show(
    run_path: Path = typer.Option(..., "--run-path", help="Path to inspect."),
) -> None:
    """Show cassette metadata and trace steps."""

    store = CassetteStore(run_path)
    try:
        store.validate()
        run = store.read_metadata()
        steps = store.read_steps()
    except CassetteError as exc:
        typer.secho(f"Cassette error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.secho(f"Cassette error: malformed cassette: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo("Cassette run.")
    _print_run(run, len(steps))
    typer.echo("steps:")
    for step in steps:
        _print_step(step)


@app.command()
def diff(
    left: Path = typer.Option(..., "--left", help="Left cassette path."),
    right: Path = typer.Option(..., "--right", help="Right cassette path."),
) -> None:
    """Diff two cassette runs."""

    try:
        summary = diff_cassettes(left, right)
    except CassetteError as exc:
        typer.secho(f"Cassette error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.secho(f"Cassette error: malformed cassette: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo("Cassette diff.")
    for key in (
        "left_run_id",
        "right_run_id",
        "final_output_changed",
        "step_count_changed",
        "step_sequence_changed",
        "latency_delta_ms",
        "cost_delta_usd",
        "changed",
    ):
        typer.echo(f"{key}: {summary[key]}")


def _print_summary(summary: dict[str, Any]) -> None:
    for key in (
        "mode",
        "expression",
        "model_output",
        "tool_output",
        "final_output",
        "step_count",
    ):
        typer.echo(f"{key}: {summary[key]}")


def _print_run(run: RunRecord, step_count: int) -> None:
    typer.echo(f"run_id: {run.run_id}")
    typer.echo(f"task: {run.task}")
    typer.echo(f"final_output: {run.final_output}")
    typer.echo(f"step_count: {step_count}")


def _print_step(step: Step) -> None:
    parts = [
        f"index: {step.index}",
        f"kind: {step.kind}",
        f"name: {step.name}",
    ]
    if step.request_hash is not None:
        parts.append(f"request_hash: {step.request_hash}")
    if step.latency_ms is not None:
        parts.append(f"latency_ms: {step.latency_ms}")
    typer.echo("  " + " | ".join(parts))
