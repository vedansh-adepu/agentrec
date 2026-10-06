Historical code blocks are illustrative records of the original 0.x project; they are not current commands.

# agentrec Project Status

## Project Name

agentrec

## Current Project Goal

Build agentrec, a deterministic record-and-replay harness for AI-agent runs.

## Core Product Sentence

agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Current Status Summary

The project has its foundational data models, request fingerprinting layer, local filesystem cassette store, fully offline fake provider/tool layer, recorder layer, hermetic replayer layer, tiny offline example math flow, CLI record/replay/show/diff/validate commands, a minimal diff engine, cassette validation safety checks, a public-facing README/demo document, a GitHub Actions test workflow, a public release readiness checklist, an MIT license, a public GitHub repository, schema-versioned cassettes, JSON output for inspection commands, and safe overwrite protection for recording. The codebase can now model, hash, store, call deterministic offline components, record model/tool/final-output events into cassette data, replay cached model/tool responses without live providers, tools, network, or APIs, demonstrate record -> replay through both a Python example API and terminal commands, inspect cassette metadata and trace steps from the terminal, compare two cassette runs from the terminal, validate cassette structure and parseability, explain the MVP clearly to a new developer, and run tests automatically on push and pull requests.

The first clean project snapshot was committed and pushed to GitHub:

- Repository: `https://github.com/vedansh-adepu/agentrec`
- Final visibility: public
- Commit: `44c4094 Initialize agentrec offline recording foundation`
- Remote: `origin https://github.com/vedansh-adepu/agentrec.git`
- Branch: `main`
- Final Git status after push: working tree clean

The repository is now public after the final readiness check passed. The visibility change modified no files, and the working tree remained clean with `main` up to date with `origin/main`.

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

### Step 14A: MIT License

Completed:

- standard MIT `LICENSE`
- README license section
- public release checklist license decision update
- project status and development log update
- repository remains private

### Step 14B: Final Public Visibility Check

Completed:

- working tree clean check
- latest commits check
- suspicious file scan
- generated private runs check
- GitHub repository visibility check
- latest GitHub Actions status check
- README, LICENSE, and public release checklist existence check

### Step 14C: Public Repository Release

Completed:

- GitHub repository visibility changed from private to public
- final visibility verified as public
- repository URL confirmed: `https://github.com/vedansh-adepu/agentrec`
- working tree remained clean
- `main` remained up to date with `origin/main`
- no files were modified during the visibility change

## Current Test Status

104 tests passing.

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

Current cassette schema version: `1`.

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
- prints JSON output for `show`, `diff`, and `validate`
- protects existing run paths unless `record --force` is explicit
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
- checks metadata schema version
- parses run metadata
- parses trace JSONL steps
- verifies trace step indexes
- reads final output when present
- parses and validates cached interaction response files
- checks response filenames against cached interaction payloads
- returns a JSON-serializable validation summary
- reports errors without raising for expected validation failures

## Next Planned Step

Post-release production hardening follow-up.

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

## What Step 14A Did

Step 14A added the MIT license only:

- created `LICENSE`
- documented MIT license in `README.md`
- marked the license decision complete in `PUBLIC_RELEASE_CHECKLIST.md`
- kept repository visibility private
- preserved runtime behavior

## What Step 14B Should Do

Step 14B completed the final public visibility check:

- verify no secrets, `.env` files, or generated private runs are tracked
- verify no virtualenvs, cache folders, or temporary/log files are present
- verify README, LICENSE, and public release checklist exist
- verify GitHub Actions CI status
- confirm the repository is safe to make public

## What Step 14C Did

Step 14C made the repository public:

- changed GitHub repository visibility from private to public
- verified final visibility as public
- kept the working tree clean
- did not modify files, commit, push, or change runtime behavior

## What Step 15 Should Do

Step 15 may do optional post-release polish:

- inspect the public GitHub page
- optionally add a README badge
- optionally verify the public clone/setup path
- keep runtime behavior unchanged unless a new implementation step is explicitly approved

## What Step 15 Must Not Do

Step 15 must not:

- add live providers without explicit approval
- add packaging release behavior without explicit approval
- add unrelated runtime behavior

## Important Design Guarantees

- Replay must eventually be hermetic.
- Replay misses must eventually raise `ReplayMissError`.
- MVP behavior must not require live network calls.
- Generated private runs should not be committed.

## Latest Step Notes

### 2026-06-03 Production Hardening Pass

Files changed:

- `README.md`
- `PRODUCTION_READINESS.md`
- `pyproject.toml`
- `examples/math_demo.py`
- `src/agentrec/cli.py`
- `src/agentrec/models.py`
- `src/agentrec/store/cassette.py`
- `src/agentrec/validation.py`
- `tests/test_cassette_store.py`
- `tests/test_cli.py`
- `tests/test_models.py`
- `tests/test_validation.py`
- `ARCHITECTURE_DECISIONS.md`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Tests run:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python examples/math_demo.py`
- `python -m pip install -e . --no-deps --target /private/tmp/agentrec-install-check`

Result:

- CLI hardening added for JSON output and explicit overwrite behavior.
- Cassette metadata now includes schema version `1`.
- Validation checks schema version, trace indexes, and response filename consistency.
- README, package metadata, production readiness docs, and offline example script improved.
- Untracked `src/.DS_Store` artifact removed.
- 104 tests passed locally.

Current status:

- Repository is public.
- Project remains fully offline.
- No live providers, dashboard, database, Docker, or paid API behavior was added.

Next step:

- Optional v0.2 follow-up work after CI verification.
