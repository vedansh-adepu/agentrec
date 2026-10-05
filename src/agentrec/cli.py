"""Command line interface for agentrec."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import typer

from agentrec.diff import diff_cassettes, diff_v2_cassettes
from agentrec.errors import CassetteError, ReplayMissError
from agentrec.examples import record_math_flow, replay_math_flow
from agentrec.models import RunRecord, Step
from agentrec.store import CassetteStore
from agentrec.validation import validate_cassette, validate_v2_cassette

app = typer.Typer(help="Record and replay offline agentrec examples.")


@app.command()
def record(
    run_path: Path = typer.Option(
        ..., "--run-path", help="Path to write the cassette."
    ),
    expression: str = typer.Option(
        "2+3", "--expression", help="Math expression to record."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing cassette directory.",
    ),
) -> None:
    """Record the offline math flow."""

    _prepare_record_path(run_path, force)
    summary = record_math_flow(run_path, expression)
    typer.echo("Recorded math flow.")
    _print_summary(summary)


@app.command()
def replay(
    run_path: Path = typer.Option(..., "--run-path", help="Path to read the cassette."),
    expression: str = typer.Option(
        "2+3", "--expression", help="Math expression to replay."
    ),
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
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show cassette metadata and trace steps."""

    if (run_path / "cassette.json").exists() or (
        run_path / "interactions.jsonl"
    ).exists():
        summary = validate_v2_cassette(run_path, level="structural")
        if not summary["ok"]:
            typer.secho(
                "Cassette error: " + "; ".join(summary["errors"]),
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        from agentrec.cassette.store import CassetteStore as V2CassetteStore

        metadata, interactions = V2CassetteStore(run_path).load()
        if json_output:
            _print_json(
                {
                    "cassette": metadata.model_dump(mode="json"),
                    "interaction_count": len(interactions),
                    "interactions": [
                        item.model_dump(mode="json") for item in interactions
                    ],
                }
            )
        else:
            typer.echo(f"Cassette schema v2: {len(interactions)} interactions")
        return

    store = CassetteStore(run_path)
    try:
        store.validate()
        run = store.read_metadata()
        steps = store.read_steps()
    except CassetteError as exc:
        typer.secho(f"Cassette error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.secho(
            f"Cassette error: malformed cassette: {exc}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        _print_json(
            {
                "run": run.model_dump(mode="json"),
                "step_count": len(steps),
                "steps": [step.model_dump(mode="json") for step in steps],
            },
        )
        return

    typer.echo("Cassette run.")
    _print_run(run, len(steps))
    typer.echo("steps:")
    for step in steps:
        _print_step(step)


@app.command()
def diff(
    left: Path = typer.Option(..., "--left", help="Left cassette path."),
    right: Path = typer.Option(..., "--right", help="Right cassette path."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
    fail_on_change: bool = typer.Option(False, "--fail-on-change"),
) -> None:
    """Diff two cassette runs."""

    if (left / "cassette.json").exists() or (right / "cassette.json").exists():
        try:
            summary = diff_v2_cassettes(left, right)
        except Exception as exc:
            typer.secho(f"error: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        if json_output:
            _print_json(summary)
        else:
            typer.echo(
                f"steps: {summary['steps']}, added: {summary['added']}, "
                f"removed: {summary['removed']}, changed: {summary['changed']}"
            )
            typer.echo(f"duration_delta_ms: {summary['duration_delta_ms']}")
            for detail in summary["details"]:
                typer.echo(
                    f"{detail['change']}: "
                    f"{detail.get('left_seq')} -> {detail.get('right_seq')}"
                )
                for field in ("request_paths", "response_paths", "error_paths"):
                    for difference in detail.get(field, []):
                        typer.echo(
                            f"  {field} {difference['path']}: "
                            f"{difference['left']} -> {difference['right']}"
                        )
        if fail_on_change and summary["behavior_changed"]:
            raise typer.Exit(code=1)
        return

    try:
        summary = diff_cassettes(left, right)
    except CassetteError as exc:
        typer.secho(f"Cassette error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.secho(
            f"Cassette error: malformed cassette: {exc}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        _print_json(summary)
        return

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


@app.command()
def validate(
    run_path: Path = typer.Option(..., "--run-path", help="Cassette path to validate."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
    level: str = typer.Option("privacy", "--level", help="Schema-v2 validation level."),
    allow_failed: bool = typer.Option(False, "--allow-failed"),
) -> None:
    """Validate cassette structure and parseability."""

    if (run_path / "cassette.json").exists() or (
        run_path / "interactions.jsonl"
    ).exists():
        try:
            summary = validate_v2_cassette(
                run_path, level=level, allow_failed=allow_failed
            )
        except ValueError as exc:
            typer.secho(f"error: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=2) from exc
        if json_output:
            _print_json(summary)
        else:
            typer.echo(f"ok: {summary['ok']}")
            typer.echo(f"level: {summary['level']}")
            typer.echo(f"interaction_count: {summary['interaction_count']}")
            for warning in summary["warnings"]:
                typer.echo(f"warning: {warning}")
            for error in summary["errors"]:
                typer.echo(f"error: {error}")
        if not summary["ok"]:
            raise typer.Exit(code=1)
        return

    summary = validate_cassette(run_path)
    if json_output:
        _print_json(summary)
        if summary["errors"]:
            raise typer.Exit(code=1)
        return

    typer.echo("Cassette validation.")
    for key in (
        "ok",
        "run_path",
        "run_id",
        "task",
        "schema_version",
        "step_count",
        "response_file_count",
        "has_final_output",
    ):
        typer.echo(f"{key}: {summary[key]}")
    if summary["errors"]:
        typer.echo("errors:")
        for error in summary["errors"]:
            typer.echo(f"  {error}")
        raise typer.Exit(code=1)


def _prepare_record_path(run_path: Path, force: bool) -> None:
    if not run_path.exists():
        return

    if run_path.is_dir() and not any(run_path.iterdir()):
        return

    if not force:
        typer.secho(
            f"Record path already exists and is not empty: {run_path}. "
            "Use --force to overwrite it.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    if run_path.is_dir():
        if (run_path / ".git").exists():
            typer.secho(
                f"Refusing to overwrite directory that contains .git: {run_path}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        shutil.rmtree(run_path)
        return

    if run_path.is_file():
        run_path.unlink()
        return

    typer.secho(
        f"Cannot overwrite unsupported path type: {run_path}",
        err=True,
        fg=typer.colors.RED,
    )
    raise typer.Exit(code=1)


def _print_json(data: dict[str, Any]) -> None:
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


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
