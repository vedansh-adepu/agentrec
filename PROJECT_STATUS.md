# agentrec Project Status

## Project Name

agentrec

## Current Project Goal

Build agentrec, a deterministic record-and-replay harness for AI-agent runs.

## Core Product Sentence

agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Current Status Summary

The project has its foundational data models, request fingerprinting layer, local filesystem cassette store, fully offline fake provider/tool layer, recorder layer, hermetic replayer layer, tiny offline example math flow, minimal CLI record/replay/show/diff/validate commands, a minimal diff engine, cassette validation safety checks, a public-facing README/demo document, a GitHub Actions test workflow, and a public release readiness checklist. The codebase can now model, hash, store, call deterministic offline components, record model/tool/final-output events into cassette data, replay cached model/tool responses without live providers, tools, network, or APIs, demonstrate record -> replay through both a Python example API and terminal commands, inspect cassette metadata and trace steps from the terminal, compare two cassette runs from the terminal, validate cassette structure and parseability, explain the MVP clearly to a new developer, and run tests automatically on push and pull requests.

The first clean project snapshot has been committed and pushed to a private GitHub repository:

- Repository: `https://github.com/vedansh-adepu/agentrec`
- Visibility: private
- Commit: `44c4094 Initialize agentrec offline recording foundation`
- Remote: `origin https://github.com/vedansh-adepu/agentrec.git`
- Branch: `main`
- Final Git status after push: working tree clean

The repository remains private. Do not make it public until the owner explicitly approves the license decision and public visibility change.

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

### Step 9: Diff Engine and CLI Diff Command

Completed:

- `diff_cassettes()`
- `agentrec diff --left <path> --right <path>`
- final output comparison
- step count comparison
- step sequence comparison
- latency and cost totals/deltas
- diff engine and CLI diff tests

### Step 10: Validate Command and Cassette Safety Checks

Completed:

- `validate_cassette()`
- `agentrec validate --run-path <path>`
- required cassette structure checks
- metadata and trace parse checks
- cached interaction response file checks
- final output presence reporting
- validation layer and CLI validate tests

### Step 11: README and Demo Documentation

Completed:

- `README.md`
- current problem and solution framing
- local setup instructions
- CLI demo commands
- cassette format explanation
- current guarantees and limitations
- roadmap and non-goals

### Step 12: GitHub Actions CI

Completed:

- `.github/workflows/tests.yml`
- push and pull request test workflow
- Python 3.11 and 3.12 test matrix
- editable install with test dependencies
- simple `pytest` run
- short README CI note

### Step 13: Final Repo Polish Before Public Release

Completed:

- README clarity pass for public-readiness
- public release checklist
- CI status note for Python 3.11 and 3.12
- private-repo and no-license status clarified
- next-step documentation for license and visibility decision

## Current Test Status

91 tests passing.

GitHub Actions CI is green for Python 3.11 and 3.12.

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
- diffs two cassette runs
- validates cassette structure and parseability
- prints simple summary output
- exits non-zero with a clear message on replay misses
- exits non-zero with a clear message on cassette inspection errors

### Diff Layer

Compares two cassette runs without live calls:

- validates both cassette folders
- compares run IDs and tasks
- compares final outputs
- compares step counts and ordered step sequences
- reports latency totals and deltas
- reports cost totals and deltas
- returns a JSON-serializable summary

### Validation Layer

Checks cassette safety without mutating files:

- checks required files and directories
- parses run metadata
- parses trace JSONL steps
- reads final output when present
- parses and validates cached interaction response files
- returns a JSON-serializable validation summary
- reports errors without raising for expected validation failures

## Next Planned Step

Step 14: license decision and public visibility decision.

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

## What Step 13 Should Do

Step 13 completed final repo polish before making the repository public:

- lightly polish README content
- add a public release checklist
- document that CI is green for Python 3.11 and 3.12
- clarify that the repo remains private
- preserve runtime behavior

## What Step 13 Must Not Do

Step 13 did not add:

- live OpenAI provider
- live Anthropic provider
- dashboard
- database
- Docker
- packaging release
- public repo visibility change unless explicitly approved

## What Step 14 Should Do

Step 14 should decide license and public visibility readiness:

- decide whether to add a license
- choose license text only after explicit owner approval
- verify no secrets, `.env` files, or generated private runs are tracked
- verify CLI demo still works if requested
- decide whether and when to make the private repository public

## What Step 14 Must Not Do

Step 14 must not:

- change repository visibility without explicit owner approval
- add a license without explicit owner approval
- add live providers
- add packaging release behavior
- add unrelated runtime behavior

## Important Design Guarantees

- Replay must eventually be hermetic.
- Replay misses must eventually raise `ReplayMissError`.
- MVP behavior must not require live network calls.
- Generated private runs should not be committed.

## Latest Step Notes

### Step 13

Files changed:

- `README.md`
- `PUBLIC_RELEASE_CHECKLIST.md`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- Not run; documentation-only change.

Result:

- Final repo polish completed before public release decision.
- Public release checklist added.
- README now notes CI is green for Python 3.11 and 3.12.
- Runtime behavior did not change.

Current status:

- Step 13 final repo polish completed.
- CI is green for Python 3.11 and 3.12.
- Repository remains private.
- Project remains fully offline.
- No source code, tests, pyproject, CI workflow, packaging, GitHub settings, repo visibility, or license files were changed.

Next step:

- Step 14: license decision and public visibility decision.
