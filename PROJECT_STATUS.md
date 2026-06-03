# agentrec Project Status

## Project Name

agentrec

## Current Project Goal

Build agentrec, a deterministic record-and-replay harness for AI-agent runs.

## Core Product Sentence

agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Current Status Summary

The project has its foundational data models, request fingerprinting layer, local filesystem cassette store, fully offline fake provider/tool layer, recorder layer, hermetic replayer layer, and a tiny offline example math flow. The codebase can now model, hash, store, call deterministic offline components, record model/tool/final-output events into cassette data, replay cached model/tool responses without live providers, tools, network, or APIs, and demonstrate record -> replay through a Python example API.

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

## Current Test Status

55 tests passing.

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

## Next Planned Step

Step 7: CLI record/replay commands.

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

## What Step 7 Should Do

Step 7 should add minimal CLI record/replay commands that:

- use Typer
- expose a small record command for the offline math flow
- expose a small replay command for the offline math flow
- remain offline and deterministic
- avoid show/diff/validate commands for now

## What Step 7 Must Not Do

Step 7 must not add:

- diff engine
- live OpenAI provider
- live Anthropic provider
- dashboard

## Important Design Guarantees

- Replay must eventually be hermetic.
- Replay misses must eventually raise `ReplayMissError`.
- MVP behavior must not require live network calls.
- Generated private runs should not be committed.

## Latest Step Notes

### Step 3

Files changed:

- `src/agentrec/providers/__init__.py`
- `src/agentrec/providers/base.py`
- `src/agentrec/providers/fake.py`
- `src/agentrec/tools/__init__.py`
- `src/agentrec/tools/registry.py`
- `src/agentrec/tools/builtin.py`
- `tests/test_fake_provider.py`
- `tests/test_tool_registry.py`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`

Current status:

- Step 3 approved.
- Project is ready for Step 4 planning and implementation after confirmation.

Next step:

- Step 4: recorder layer.

### Docs-Only Production Workflow Setup

Files changed:

- `DEVELOPMENT_LOG.md`
- `ARCHITECTURE_DECISIONS.md`
- `QUALITY_CHECKLIST.md`
- `PRODUCTION_STANDARDS.md`
- `AGENTS.md`
- `PROJECT_STATUS.md`

Tests run:

- Not run; documentation-only change.

Current status:

- Production workflow documentation is in place.
- No runtime behavior changed.

Next step:

- Step 4: recorder layer, after confirmation.

### Step 4

Files changed:

- `src/agentrec/core/__init__.py`
- `src/agentrec/core/recorder.py`
- `tests/test_recorder.py`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`

Current status:

- Step 4 recorder layer completed.
- Project remains fully offline.
- No replayer, CLI, diff engine, live providers, dashboard, database, Docker, CI, or packaging work was added.

Next step:

- Step 5: replayer layer.

### GitHub Push: First Private Repository Snapshot

Files changed:

- `DEVELOPMENT_LOG.md`
- `PROJECT_STATUS.md`

Tests run:

- Not run for this documentation-only milestone update.
- Before the push, 37 tests passed with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`.

Current status:

- Private GitHub repository pushed: `https://github.com/vedansh-adepu/agentrec`
- Commit pushed: `44c4094 Initialize agentrec offline recording foundation`
- Remote: `origin https://github.com/vedansh-adepu/agentrec.git`
- Branch: `main`
- Final Git status after push: working tree clean
- No Step 5 work was implemented during push.

Next step:

- Step 5: replayer layer.

### Step 5

Files changed:

- `src/agentrec/core/__init__.py`
- `src/agentrec/core/replayer.py`
- `tests/test_replayer.py`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`

Current status:

- Step 5 replayer layer completed.
- Project remains fully offline and replay is hermetic for cached model/tool interactions.
- Missing cached model/tool interactions raise `ReplayMissError`.
- No CLI, fake/example agent flow, show command, diff engine, validate command, live providers, dashboard, database, Docker, GitHub Actions, or packaging release was added.

Next step:

- Step 6: example offline agent flow.

### Step 6

Files changed:

- `src/agentrec/examples/__init__.py`
- `src/agentrec/examples/math_flow.py`
- `tests/test_example_math_flow.py`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`

Current status:

- Step 6 example offline agent flow completed.
- The flow records a math cassette and replays matching model/tool/final output through Python functions.
- Project remains fully offline.
- No CLI commands, show command, diff engine, validate command, live providers, dashboard, database, Docker, GitHub Actions, or packaging release was added.

Next step:

- Step 7: CLI record/replay commands.
