# agentrec Project Status

## Project Name

agentrec

## Current Project Goal

Build agentrec, a deterministic record-and-replay harness for AI-agent runs.

## Core Product Sentence

agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Current Status Summary

The project has its foundational data models, request fingerprinting layer, local filesystem cassette store, fully offline fake provider/tool layer, and a recorder layer. The codebase is still pre-replayer: it can model, hash, store, call deterministic offline components, and record model/tool/final-output events into cassette data, but it does not yet replay from cassette data.

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

## Current Test Status

37 tests passing.

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

## Next Planned Step

Step 5: replayer layer.

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

## What Step 5 Should Do

Step 5 should add a small replayer layer that:

- reads cached model interactions from `CassetteStore`
- reads cached tool interactions from `CassetteStore`
- returns cached responses without calling live providers or tools
- raises `ReplayMissError` for missing cached responses
- stays fully offline and hermetic

## What Step 5 Must Not Do

Step 5 must not add:

- CLI commands
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
