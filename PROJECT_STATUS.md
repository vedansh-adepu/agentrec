# agentrec Project Status

## Project Name

agentrec

## Current Project Goal

Build agentrec, a deterministic record-and-replay harness for AI-agent runs.

## Core Product Sentence

agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Current Status Summary

The project has its foundational data models, request fingerprinting layer, local filesystem cassette store, fully offline fake provider/tool layer, recorder layer, hermetic replayer layer, tiny offline example math flow, and minimal CLI record/replay/show commands. The codebase can now model, hash, store, call deterministic offline components, record model/tool/final-output events into cassette data, replay cached model/tool responses without live providers, tools, network, or APIs, demonstrate record -> replay through both a Python example API and terminal commands, and inspect cassette metadata and trace steps from the terminal.

The first clean project snapshot has been committed and pushed to a private GitHub repository:

- Repository: `https://github.com/vedansh-adepu/agentrec`
- Visibility: private
- Commit: `44c4094 Initialize agentrec offline recording foundation`
- Remote: `origin https://github.com/vedansh-adepu/agentrec.git`
- Branch: `main`
- Final Git status after push: working tree clean

Do not make the repository public until the replayer, CLI, README/demo, and CI are stronger.

The repository now also has persistent production workflow documentation for development history, architecture decisions, quality checks, and production standards.

## Completed Steps

### Step 1: Project Foundation

Completed:

- project configuration
- package skeleton
- Pydantic models
- request normalizer
- SHA-256 request hashing
- tests for model serialization and stable hashing

### Step 2: Cassette Store

Completed:

- custom error hierarchy
- local filesystem `CassetteStore`
- cassette metadata storage
- trace JSONL storage
- cached interaction response files
- final output artifact storage
- cassette validation
- cassette store tests

### Step 3: Offline Provider and Tool Layer

Completed:

- provider base types
- deterministic `FakeModelProvider`
- simple `ToolRegistry`
- `ToolResult` model
- safe built-in calculator tool
- default tool registry
- fake provider and tool registry tests

### Step 4: Recorder Layer

Completed:

- `AgentRecorder`
- cassette initialization through the recorder constructor
- recorded model calls
- recorded tool calls
- final output recording
- ordered trace steps
- cached interactions for model/tool calls
- metadata final output updates
- recorder tests

### Step 5: Replayer Layer

Completed:

- `AgentReplayer`
- cassette validation during replayer construction
- cached model response replay
- cached tool result replay
- final output reading
- `ReplayMissError` on missing model/tool cached interactions
- read-only cassette replay behavior
- replayer tests

### Step 6: Example Offline Agent Flow

Completed:

- `record_math_flow()`
- `replay_math_flow()`
- offline math cassette recording
- offline math cassette replay
- record/replay summary dictionaries
- example flow tests

### Step 7: CLI Record/Replay Commands

Completed:

- Typer `agentrec` app
- `agentrec record --run-path <path> --expression <expr>`
- `agentrec replay --run-path <path> --expression <expr>`
- console script entry point
- replay miss CLI error handling
- CLI tests

### Step 8: CLI Show Command

Completed:

- `agentrec show --run-path <path>`
- cassette metadata inspection
- ordered trace step inspection
- clear CLI errors for missing or malformed cassettes
- show command tests

## Current Test Status

68 tests passing.

Last known command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider
```

## Current Architecture Layers

### Fingerprint Layer

Normalizes request data and computes stable SHA-256 hashes for content-addressed lookup.

### Cassette Storage Layer

Writes and reads cassette files on disk:

- `metadata.json`
- `trace.jsonl`
- `responses/<request_hash>_<kind>.json`
- `artifacts/final_output.txt`

### Offline Provider/Tool Layer

Provides deterministic local model and tool behavior through:

- `FakeModelProvider`
- `ToolRegistry`
- built-in calculator tool

### Recorder Layer

Coordinates offline provider and tool calls with cassette storage:

- records model requests/responses
- records tool requests/results
- writes cached interactions
- appends ordered trace steps
- writes final output artifacts
- updates run metadata

### Replayer Layer

Reads cached cassette interactions without accepting providers or tool registries:

- replays model responses from cached interactions
- replays tool results from cached interactions
- raises `ReplayMissError` on cache misses
- reads final output artifacts
- avoids cassette mutation during replay

### Example Flow Layer

Demonstrates the current offline engine through a Python API:

- records a simple math task into a cassette
- replays the same model/tool calls from the cassette
- verifies final output, model output, and tool output match
- stays independent of CLI commands

### CLI Layer

Exposes the offline math flow through terminal commands:

- records an offline math cassette
- replays an offline math cassette
- shows cassette metadata and trace steps
- prints simple summary output
- exits non-zero with a clear message on replay misses
- exits non-zero with a clear message on cassette inspection errors

## Next Planned Step

Step 9: diff engine and diff command.

## Persistent Project Memory

Before each new step, Codex should read:

- `PROJECT_BRIEF.md`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`
- `ARCHITECTURE_DECISIONS.md`
- `QUALITY_CHECKLIST.md`
- `PRODUCTION_STANDARDS.md`

After each completed step, Codex should update:

- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

`ARCHITECTURE_DECISIONS.md` should be updated only when a major design decision is introduced or changed.

## What Step 9 Should Do

Step 9 should add a focused diff layer and CLI command that:

- compares two existing cassettes
- reports final output changes
- reports tool sequence changes
- reports step changes
- reports cost and latency differences where data exists
- keeps output simple and inspectable
- remains offline and deterministic
- avoids validate command for now

## What Step 9 Must Not Do

Step 9 must not add:

- validate command
- live OpenAI provider
- live Anthropic provider
- dashboard

## Important Design Guarantees

- Replay must eventually be hermetic.
- Replay misses must eventually raise `ReplayMissError`.
- MVP behavior must not require live network calls.
- Generated private runs should not be committed.

## Latest Step Notes

### Step 8

Files changed:

- `src/agentrec/cli.py`
- `tests/test_cli.py`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`

Result:

- 68 tests passed.

Current status:

- Step 8 show command completed.
- Project remains fully offline.
- No diff command, diff engine, validate command, live providers, CI, dashboard, database, Docker, GitHub Actions, or packaging release was added.

Next step:

- Step 9: diff engine and diff command.
