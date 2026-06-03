# agentrec Development Log

This log records the chronological engineering history of agentrec for debugging, review, and future handoff.

## 2026-06-02 - Step 1: Project Foundation

- Goal: Create the project foundation for deterministic record/replay work.
- Files changed:
  - `PROJECT_BRIEF.md`
  - `AGENTS.md`
  - `.gitignore`
  - `pyproject.toml`
  - `src/agentrec/__init__.py`
  - `src/agentrec/models.py`
  - `src/agentrec/normalizer.py`
  - `src/agentrec/hashing.py`
  - `src/agentrec/py.typed`
  - `tests/test_hashing.py`
  - `tests/test_models.py`
- Key implementation notes:
  - Added beginner-friendly project brief and repository instructions.
  - Added Pydantic models for usage, steps, run records, and cached interactions.
  - Added request normalization.
  - Added SHA-256 request hashing.
  - Added hashing and model serialization tests.
  - Fixed overly aggressive removal of generic `id` during normalization so meaningful tool IDs are preserved.
- Tests run:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`
- Result:
  - 7 tests passed.
- Bugs/issues found:
  - Initial normalizer removed any key named `id`, which could collapse distinct tool requests.
- Decisions made:
  - Preserve meaningful `id` fields.
  - Remove only clearly unstable fields such as `request_id`, `trace_id`, `span_id`, `run_id`, timestamps, and random IDs.
- Next step:
  - Step 2: local filesystem cassette store.

## 2026-06-02 - Step 2: Cassette Store

- Goal: Add a local filesystem storage layer for cassette data.
- Files changed:
  - `src/agentrec/errors.py`
  - `src/agentrec/store/__init__.py`
  - `src/agentrec/store/cassette.py`
  - `tests/test_cassette_store.py`
- Key implementation notes:
  - Added custom errors.
  - Added `CassetteStore`.
  - Added storage layout:
    - `metadata.json`
    - `trace.jsonl`
    - `responses/`
    - `artifacts/`
    - `artifacts/final_output.txt`
  - Added cassette tests for initialization, metadata, steps, interactions, final output, and validation.
- Tests run:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`
- Result:
  - 15 tests passed.
- Bugs/issues found:
  - None in final Step 2 review.
- Decisions made:
  - Use inspectable local filesystem cassettes before any remote or database-backed storage.
- Next step:
  - Step 3: fake model provider and tool registry.

## 2026-06-02 - Step 3: Fake Provider and Tool Registry

- Goal: Add deterministic offline model and tool components for future recorder/replayer layers.
- Files changed:
  - `src/agentrec/providers/__init__.py`
  - `src/agentrec/providers/base.py`
  - `src/agentrec/providers/fake.py`
  - `src/agentrec/tools/__init__.py`
  - `src/agentrec/tools/registry.py`
  - `src/agentrec/tools/builtin.py`
  - `tests/test_fake_provider.py`
  - `tests/test_tool_registry.py`
- Key implementation notes:
  - Added `ModelRequest`, `ModelResponse`, and `ModelProvider`.
  - Added deterministic `FakeModelProvider`.
  - Added `ToolRegistry` and `ToolResult`.
  - Added safe AST-based calculator tool.
  - Added provider and tool tests.
- Tests run:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`
- Result:
  - 28 tests passed.
- Bugs/issues found:
  - None in final Step 3 review.
- Decisions made:
  - Keep provider and tool behavior fully offline and deterministic.
  - Use AST parsing for calculator safety instead of `eval`.
- Next step:
  - Documentation/status production workflow setup, then Step 4: recorder layer.

## 2026-06-02 - Docs/Status Sync: Persistent Project Memory

- Goal: Add persistent current-state tracking and require Codex to read project context before new steps.
- Files changed:
  - `PROJECT_STATUS.md`
  - `AGENTS.md`
- Key implementation notes:
  - Added `PROJECT_STATUS.md` as the persistent current-state tracker.
  - Updated `AGENTS.md` to require reading `PROJECT_BRIEF.md` and `PROJECT_STATUS.md` before new steps.
  - No runtime behavior changed.
- Tests run:
  - Not run; documentation-only change.
- Result:
  - Project is ready for production workflow documentation.
- Bugs/issues found:
  - None.
- Decisions made:
  - Keep status tracking explicit between implementation steps.
- Next step:
  - Docs-only production workflow setup.

## 2026-06-02 - Docs-Only Production Workflow Setup

- Goal:
  - Establish production-grade project memory, architecture decision tracking, quality gates, and production standards before implementing the recorder layer.
- Files changed:
  - `DEVELOPMENT_LOG.md`
  - `ARCHITECTURE_DECISIONS.md`
  - `QUALITY_CHECKLIST.md`
  - `PRODUCTION_STANDARDS.md`
  - `AGENTS.md`
  - `PROJECT_STATUS.md`
- Key implementation notes:
  - Added architecture decision records for major project choices.
  - Added quality checklist for scope, tests, replay safety, storage safety, error handling, docs, Git hygiene, and security/privacy.
  - Added production standards defining production-level as strong guarantees, focused architecture, tests, docs, and safety rather than feature bloat.
  - Updated `AGENTS.md` so future Codex sessions read the full project memory set before each step.
  - Updated `PROJECT_STATUS.md` to mention the persistent production workflow documentation.
  - No runtime behavior changed.
- Tests run:
  - Not run; documentation-only change.
- Result:
  - Persistent production workflow documentation is in place.
  - Project remains ready for Step 4: recorder layer.
- Bugs/issues found:
  - None.
- Decisions made:
  - Keep production methodology lightweight but explicit.
  - Treat persistent project memory as part of the engineering workflow.
- Next step:
  - Step 4: recorder layer.

## 2026-06-02 - Step 4: Recorder Layer

- Goal:
  - Implement a small offline recorder layer that connects request hashing, cassette storage, the fake model provider, and the tool registry.
- Files changed:
  - `src/agentrec/core/__init__.py`
  - `src/agentrec/core/recorder.py`
  - `tests/test_recorder.py`
  - `PROJECT_STATUS.md`
  - `DEVELOPMENT_LOG.md`
- Key implementation notes:
  - Added `AgentRecorder`.
  - The recorder constructor initializes the cassette store with the provided `RunRecord`.
  - `record_model_call()` hashes model requests, calls the offline provider, records latency, writes a model `CachedInteraction`, and appends a model trace step.
  - `record_tool_call()` hashes tool requests, calls the local `ToolRegistry`, records latency, writes a tool `CachedInteraction`, and appends a tool trace step.
  - `finish()` writes `final_output.txt`, appends a final trace step, updates `RunRecord.final_output`, and writes updated metadata.
  - Step indexes start at 0 and increment for every model, tool, and final step.
  - Unknown tool errors are not swallowed.
  - No runtime behavior outside recording was added.
- Tests run:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/agentrec-test-deps python -m pytest -p no:cacheprovider`
- Result:
  - 37 tests passed.
- Bugs/issues found:
  - None.
- Decisions made:
  - Use constructor initialization for the recorder so a recorder instance always starts with an initialized cassette.
  - Keep the recorder as a narrow coordinator layer, not a replayer or CLI.
- Next step:
  - Step 5: replayer layer.

## Future Entry Template

## YYYY-MM-DD - Step N: <name>

- Goal:
- Files changed:
- Key implementation notes:
- Tests run:
- Result:
- Bugs/issues found:
- Decisions made:
- Next step:
