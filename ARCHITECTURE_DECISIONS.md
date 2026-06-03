# agentrec Architecture Decisions

This file records important architecture decisions and the reasoning behind them.

## ADR-001: Build a Local Deterministic Record/Replay CLI, Not a Dashboard

- Status: Accepted
- Context:
  - The core problem is reproducibility of AI-agent runs, not visualization.
  - A dashboard would add surface area before the engine proves record/replay behavior.
- Decision:
  - Build a local deterministic record/replay CLI first.
  - Do not build a web dashboard during the MVP.
- Consequences:
  - Development stays focused on core guarantees.
  - Terminal workflows remain easy to test.
  - UI work can wait until the engine is trustworthy.

## ADR-002: Start With Fake/Offline Provider Before Live OpenAI/Anthropic Providers

- Status: Accepted
- Context:
  - Live providers introduce network, credentials, rate limits, cost, and nondeterminism.
  - The MVP must prove deterministic record/replay behavior first.
- Decision:
  - Start with a deterministic fake provider.
  - Do not add live OpenAI or Anthropic providers until the offline MVP is correct.
- Consequences:
  - Tests can run without secrets or network access.
  - Provider abstractions can be shaped by local behavior before live integrations.

## ADR-003: Use Content-Addressed Request Hashes for Replay Lookup

- Status: Accepted
- Context:
  - Replay must find the cached response for the exact meaningful request.
  - Raw request payloads may contain unstable metadata.
- Decision:
  - Normalize request data and compute SHA-256 hashes for cassette lookup.
- Consequences:
  - Replay lookup can be deterministic.
  - Request normalization must be conservative and well-tested.
  - Meaningful request changes should produce different hashes.

## ADR-004: Preserve Meaningful `id` Fields During Normalization

- Status: Accepted
- Context:
  - A generic `id` field can be meaningful in tool arguments, such as `{"id": "customer_123"}`.
  - Removing all `id` keys could make different tool requests hash to the same value.
- Decision:
  - Do not remove generic `id`.
  - Remove clearly unstable fields such as `request_id`, `trace_id`, `span_id`, `run_id`, timestamps, and random IDs.
- Consequences:
  - Tool requests with meaningful IDs stay distinguishable.
  - Future normalizer changes should avoid broad field deletion.

## ADR-005: Use Local Filesystem Cassettes First

- Status: Accepted
- Context:
  - Cassettes should be easy to inspect, diff, and test.
  - Remote storage or databases would add complexity before the MVP needs them.
- Decision:
  - Store cassettes on the local filesystem.
  - Use simple files: `metadata.json`, `trace.jsonl`, `responses/`, and `artifacts/`.
- Consequences:
  - Cassettes are transparent and easy to debug.
  - Filesystem tests can use `tmp_path`.
  - Remote storage remains a future option.

## ADR-006: Keep Replay Hermetic; Cache Misses Must Fail Loudly

- Status: Accepted
- Context:
  - Replay loses its value if it silently falls back to live APIs, live models, network calls, or real tools.
  - Missing cached responses should expose drift or incomplete recordings.
- Decision:
  - Replay mode must be hermetic.
  - Replay cache misses must eventually raise `ReplayMissError`.
- Consequences:
  - Tests can trust replayed runs.
  - Missing cassette data becomes visible immediately.
  - Replayer implementation must avoid any live fallback path.

## ADR-007: Use Safe AST Parsing for Calculator Instead of `eval`

- Status: Accepted
- Context:
  - The built-in calculator should support simple arithmetic.
  - Direct `eval` would be unsafe and unnecessary.
- Decision:
  - Parse expressions with `ast`.
  - Allow only numeric constants, `+`, `-`, `*`, `/`, parentheses, and unary signs.
- Consequences:
  - Calculator behavior is safe and deterministic.
  - Unsafe expressions are rejected with clear errors.

## ADR-008: Work One Step at a Time and Inspect Before Moving Forward

- Status: Accepted
- Context:
  - The project needs disciplined scope control.
  - Each layer should be reviewed before the next layer is added.
- Decision:
  - Work one approved step at a time.
  - Inspect and review files before moving to the next step.
- Consequences:
  - Scope drift is easier to catch.
  - Project state stays understandable.
  - Documentation and tests can stay aligned with implementation.

## ADR-009: Treat Production-Level as Strong Guarantees, Tests, Docs, and Safety, Not Feature Bloat

- Status: Accepted
- Context:
  - Production-grade work does not require adding dashboards, databases, Docker, cloud sync, auth, or live providers early.
  - The MVP should stay small while preserving serious engineering standards.
- Decision:
  - Define production-level as focused scope with strong guarantees, tests, clear errors, safe defaults, and useful documentation.
- Consequences:
  - The project avoids premature infrastructure.
  - Quality is measured by reliability and clarity rather than feature count.
  - Future additions must serve the core record/replay goal.
