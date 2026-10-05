"""Command-line inspection and maintenance for schema-v2 cassettes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from . import __version__
from .cassette.replay import ReplayIndex
from .cassette.store import CassetteStore
from .diff import diff_v2_cassettes
from .matching import MatchPolicy
from .redaction import scrub as scrub_cassette
from .validation import ValidationLevel, validate_v2_cassette

app = typer.Typer(
    help="Inspect and validate deterministic AI-agent cassettes.",
    invoke_without_command=True,
)


def _fail(ctx: typer.Context, exc: Exception, *, code: int) -> None:
    if ctx.obj and ctx.obj.get("debug"):
        raise exc
    typer.echo(f"error: {str(exc).splitlines()[0]}", err=True)
    raise typer.Exit(code=code) from exc


def _json(data: dict[str, Any]) -> None:
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


@app.callback()
def main(
    ctx: typer.Context,
    debug: Annotated[
        bool, typer.Option("--debug", help="Show error traceback.")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", is_eager=True, help="Print version and exit.")
    ] = False,
) -> None:
    """Configure CLI error display and global version output."""
    ctx.obj = {"debug": debug}
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=2)


@app.command()
def version() -> None:
    """Print the installed agentrec version."""
    typer.echo(__version__)


@app.command()
def show(
    ctx: typer.Context,
    cassette: Annotated[Path, typer.Argument(help="Cassette directory.")],
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    """Show schema-v2 metadata and ordered interactions."""
    try:
        result = validate_v2_cassette(cassette, level=ValidationLevel.STRUCTURAL)
        if not result["ok"]:
            raise ValueError("; ".join(result["errors"]))
        metadata, interactions = CassetteStore(cassette).load()
    except Exception as exc:
        _fail(ctx, exc, code=2)
    if json_output:
        _json(
            {
                "cassette": metadata.model_dump(mode="json"),
                "interaction_count": len(interactions),
                "interactions": [item.model_dump(mode="json") for item in interactions],
            }
        )
        return
    typer.echo(f"schema_version: {metadata.schema_version}")
    typer.echo(f"status: {metadata.status}")
    typer.echo(f"interactions: {len(interactions)}")
    for item in interactions:
        name = (
            item.request["name"]
            if item.kind == "tool"
            else f"{item.request['method']} {item.request['url']}"
        )
        outcome = "error" if item.error else "response"
        typer.echo(
            f"{item.seq}: {item.kind} {name} occurrence={item.occurrence} {outcome}"
        )


@app.command()
def diff(
    ctx: typer.Context,
    left: Annotated[Path, typer.Argument(help="First cassette.")],
    right: Annotated[Path, typer.Argument(help="Second cassette.")],
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    fail_on_change: Annotated[
        bool, typer.Option("--fail-on-change", help="Exit 1 if behavior changed.")
    ] = False,
) -> None:
    """Compare every schema-v2 request, response, error, and trajectory step."""
    try:
        result = diff_v2_cassettes(left, right)
    except Exception as exc:
        _fail(ctx, exc, code=2)
    if json_output:
        _json(result)
    else:
        typer.echo(
            f"steps: {result['steps']}, added: {result['added']}, "
            f"removed: {result['removed']}, changed: {result['changed']}"
        )
        typer.echo(f"duration_delta_ms: {result['duration_delta_ms']}")
        for detail in result["details"]:
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
    if fail_on_change and result["behavior_changed"]:
        raise typer.Exit(code=1)


@app.command()
def validate(
    ctx: typer.Context,
    cassette: Annotated[Path, typer.Argument(help="Cassette directory.")],
    level: Annotated[
        str, typer.Option("--level", help="Validation level.")
    ] = "privacy",
    privacy: Annotated[
        bool, typer.Option("--privacy", help="Include privacy checks.")
    ] = False,
    allow_failed: Annotated[
        bool, typer.Option("--allow-failed", help="Accept failed recordings.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    """Check structural, integrity, replayability, and privacy guarantees."""
    try:
        selected = ValidationLevel.PRIVACY if privacy else ValidationLevel(level)
        result = validate_v2_cassette(
            cassette, level=selected, allow_failed=allow_failed
        )
    except Exception as exc:
        _fail(ctx, exc, code=2)
    if json_output:
        _json(result)
    elif not result["ok"]:
        typer.echo(
            "error: " + "; ".join(str(e).splitlines()[0] for e in result["errors"]),
            err=True,
        )
    else:
        typer.echo(f"ok: {result['ok']}")
        typer.echo(f"level: {result['level']}")
        typer.echo(f"interaction_count: {result['interaction_count']}")
        for warning in result["warnings"]:
            typer.echo(f"warning: {warning}")
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command()
def scrub(
    ctx: typer.Context,
    cassette: Annotated[Path, typer.Argument(help="Owned cassette directory.")],
) -> None:
    """Reapply current redaction rules to an owned cassette atomically."""
    try:
        changed = scrub_cassette(cassette)
    except Exception as exc:
        _fail(ctx, exc, code=2)
    typer.echo(f"scrubbed interactions: {changed}")


@app.command("inspect-miss")
def inspect_miss(
    ctx: typer.Context,
    cassette: Annotated[Path, typer.Argument(help="Cassette directory.")],
    request_json: Annotated[Path, typer.Argument(help="JSON request file.")],
) -> None:
    """Explain whether a JSON HTTP or tool request matches a recorded key."""
    try:
        validation = validate_v2_cassette(cassette, level="integrity")
        if not validation["ok"]:
            raise ValueError("; ".join(validation["errors"]))
        metadata, interactions = CassetteStore(cassette).load()
        request = json.loads(request_json.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request JSON must be an object")
        config = metadata.match_policy.config
        policy = MatchPolicy(
            name=metadata.match_policy.name,
            version=metadata.match_policy.version,
            ignore_body_paths=tuple(config.get("ignore_body_paths", [])),
            ignore_query=tuple(config.get("ignore_query", [])),
            match_headers=tuple(config.get("match_headers", [])),
        )
        kind = request.get("kind")
        if kind == "tool":
            key = policy.tool_key(request["name"], request["arguments"])
        elif kind == "http":
            key = policy.http_key(
                request["method"],
                request["url"],
                request.get("body"),
                request.get("headers", {}),
            )
        else:
            raise ValueError("request kind must be 'http' or 'tool'")
        played = ReplayIndex(interactions).play(key, request)
    except Exception as exc:
        _fail(ctx, exc, code=1 if "replay" in type(exc).__name__.lower() else 2)
    typer.echo(
        f"match: seq={played.seq} occurrence={played.occurrence} key={played.key}"
    )
