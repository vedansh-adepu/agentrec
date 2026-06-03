"""Command line interface for agentrec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from agentrec.errors import ReplayMissError
from agentrec.examples import record_math_flow, replay_math_flow

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
