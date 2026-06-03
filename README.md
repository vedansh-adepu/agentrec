# agentrec

agentrec is a deterministic record-and-replay harness for AI-agent runs. It records model and tool interactions into local content-addressed cassettes, then replays those interactions hermetically so agent behavior becomes reproducible, inspectable, diffable, and testable.

## The Problem

AI-agent runs are hard to test because they often change between executions. Model outputs can vary, tool calls can follow different paths, latency and cost can drift, and final answers can change even when the task looks the same. That makes debugging, reviewing regressions, and building reliable test fixtures difficult.

## The Solution

agentrec makes agent runs reproducible by recording the important interactions in a local cassette. A cassette stores normalized request hashes, model responses, tool results, trace steps, metadata, timing, usage, and final output.

The current MVP supports this offline workflow:

- `record`: run the offline example once and save model/tool interactions into a cassette.
- `replay`: serve the same model/tool responses from cassette data without live calls.
- `show`: inspect run metadata and ordered trace steps.
- `diff`: compare two cassette runs by final output, step count, step sequence, latency, and cost totals.
- `validate`: check cassette structure and parseability before inspection, replay, or diffing.

## Current Demo

The current demo is intentionally small: an offline math flow using a fake model provider and a calculator tool.

```bash
agentrec record --run-path runs/math_001 --expression "2+3"
agentrec replay --run-path runs/math_001 --expression "2+3"
agentrec show --run-path runs/math_001
agentrec diff --left runs/math_001 --right runs/math_002
agentrec validate --run-path runs/math_001
```

To diff two runs, record another cassette first:

```bash
agentrec record --run-path runs/math_002 --expression "2+4"
agentrec diff --left runs/math_001 --right runs/math_002
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pytest
```

## CI

Tests pass on GitHub Actions for Python 3.11 and 3.12.

## Cassette Format

agentrec stores runs in a local filesystem cassette:

```text
metadata.json
trace.jsonl
responses/
artifacts/final_output.txt
```

The current response files use this shape:

```text
responses/<request_hash>_<kind>.json
```

where `kind` is `model` or `tool`.

## Current Production Guarantees

- Replay is hermetic for cached model and tool interactions.
- Replay misses raise `ReplayMissError`.
- Cassette inspection is read-only.
- Diff is read-only.
- Validation is read-only and reports structural problems.
- Tests run offline.
- No live OpenAI or Anthropic providers are implemented in the current MVP.

## Current Status

- 91 tests passing.
- Tests pass through GitHub Actions CI on Python 3.11 and 3.12.
- Offline math demo only.
- Repository remains private for now.
- Live providers are not implemented yet.
- CLI commands currently available: `record`, `replay`, `show`, `diff`, and `validate`.
- No license has been added yet.

## Limitations

- No live provider integrations yet.
- No LangChain or LangGraph adapters yet.
- The example flow currently uses a fake provider and calculator tool.
- No public release or package publishing yet.
- The CLI is intentionally plain and line-oriented.

## Roadmap

- License decision before public visibility.
- Optional README badge.
- Richer demo screenshots or terminal captures.
- Optional live provider wrappers.
- LangChain/LangGraph adapter.
- Richer diff output.
- Safer overwrite policy for record command.
- Public release later, after the offline MVP and project documentation are stronger.

## Non-Goals for the Current MVP

- Web dashboard.
- Database-backed storage.
- Docker setup.
- Live OpenAI or Anthropic provider support.
- Cloud sync or hosted tracing backend.
- Public repository visibility.

## Development Notes

Generated private runs should not be committed. The repository ignores `runs/`, `.env` files, virtual environments, caches, and common editor/OS files.
