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

Recording refuses to overwrite an existing non-empty run path unless `--force` is explicit:

```bash
agentrec record --run-path runs/math_001 --expression "2+3" --force
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pytest
```

After installation from a local clone, the `agentrec` console command is available from the active environment.

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

`metadata.json` includes a `schema_version` field. The current cassette schema version is `1`.

## Command Output and Exit Codes

`show`, `diff`, and `validate` support machine-readable output:

```bash
agentrec show --run-path runs/math_001 --json
agentrec diff --left runs/math_001 --right runs/math_002 --json
agentrec validate --run-path runs/math_001 --json
```

Exit codes:

- `0`: success
- `1`: replay miss, validation failure, cassette error, or record overwrite policy failure
- `2`: Typer usage/configuration error

## Example Transcript

```bash
$ agentrec record --run-path runs/math_001 --expression "2+3"
Recorded math flow.
mode: record
expression: 2+3
model_output: Use the calculator tool for: calculate 2+3
tool_output: {'result': 5}
final_output: 5
step_count: 3

$ agentrec replay --run-path runs/math_001 --expression "2+3"
Replayed math flow.
mode: replay
expression: 2+3
model_output: Use the calculator tool for: calculate 2+3
tool_output: {'result': 5}
final_output: 5
step_count: 3

$ agentrec show --run-path runs/math_001
Cassette run.
run_id: math_flow
task: Calculate 2+3
final_output: 5
step_count: 3
steps:
  index: 0 | kind: model | name: fake-math | request_hash: <hash> | latency_ms: <ms>
  index: 1 | kind: tool | name: calculator | request_hash: <hash> | latency_ms: <ms>
  index: 2 | kind: final | name: final_output

$ agentrec validate --run-path runs/math_001
Cassette validation.
ok: True
run_path: runs/math_001
run_id: math_flow
task: Calculate 2+3
schema_version: 1
step_count: 3
response_file_count: 2
has_final_output: True
```

## Current Production Guarantees

- Replay is hermetic for cached model and tool interactions.
- Replay misses raise `ReplayMissError`.
- Cassette inspection is read-only.
- Diff is read-only.
- Validation is read-only and reports structural problems.
- Tests run offline.
- No live OpenAI or Anthropic providers are implemented in the current MVP.

## Current Status

- Test suite runs locally and in GitHub Actions.
- Tests pass through GitHub Actions CI on Python 3.11 and 3.12.
- Offline math demo only.
- Repository is public.
- Live providers are not implemented yet.
- CLI commands currently available: `record`, `replay`, `show`, `diff`, and `validate`.
- Licensed under the MIT License.

## Limitations

- No live provider integrations yet.
- No LangChain or LangGraph adapters yet.
- The example flow currently uses a fake provider and calculator tool.
- No package publishing yet.
- The CLI is intentionally plain and line-oriented.

## Roadmap

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

## License

agentrec is licensed under the MIT License. See `LICENSE` for details.
