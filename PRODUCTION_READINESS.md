# Production Readiness

This document describes what agentrec supports today and what remains before a larger release.

## What Works Today

- Offline record/replay flow for a deterministic math example.
- Local filesystem cassettes with content-addressed model and tool interactions.
- Hermetic replay for cached model and tool requests.
- `ReplayMissError` on missing cached replay interactions.
- CLI commands for `record`, `replay`, `show`, `diff`, and `validate`.
- JSON output for `show`, `diff`, and `validate`.
- Safe record overwrite behavior through explicit `--force`.
- Cassette schema version `1` in run metadata.
- Cassette validation for required files, schema version, trace parsing, response parsing, final output presence, and response filename consistency.
- Offline tests and GitHub Actions CI for Python 3.11 and 3.12.

## Intentionally Not Supported Yet

- Live OpenAI provider.
- Live Anthropic provider.
- Live Gemini or other external LLM providers.
- API keys or paid APIs.
- LangChain or LangGraph adapters.
- Web dashboard.
- Database-backed storage.
- Docker setup.
- Package publishing to PyPI.

## Real Usage Checklist

1. Install from a local clone:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[test]"
   ```

2. Record an offline cassette:

   ```bash
   agentrec record --run-path runs/math_001 --expression "2+3"
   ```

3. Replay the same cassette:

   ```bash
   agentrec replay --run-path runs/math_001 --expression "2+3"
   ```

4. Inspect and validate:

   ```bash
   agentrec show --run-path runs/math_001
   agentrec validate --run-path runs/math_001
   ```

5. Use `--force` only when intentionally replacing an existing local cassette:

   ```bash
   agentrec record --run-path runs/math_001 --expression "2+3" --force
   ```

## Remaining v0.2 Tasks

- Add optional README badge and richer terminal demo assets.
- Add a safer record path policy for broader user workflows.
- Add pytest fixtures for cassette replay tests.
- Add optional framework adapters after the offline core remains stable.
- Add live provider wrappers only after the offline MVP guarantees are preserved.
- Decide whether and when to publish a package.
