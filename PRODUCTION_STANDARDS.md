# agentrec Production Standards

Production-level does not mean overbuilding.

For agentrec, production-level means small scope with strong guarantees. The MVP should remain focused, but the engineering standards should be real: deterministic behavior, hermetic replay, clear errors, typed models, safe defaults, strong tests, and useful documentation.

## Core Standard

The product must eventually prove:

```text
record -> replay -> show -> diff -> test
```

Each layer should move the project closer to that standard without adding unrelated infrastructure.

## Required Engineering Qualities

- Deterministic behavior where expected.
- Hermetic replay.
- Replay misses raise clear errors.
- Typed models for persisted and exchanged data.
- Inspectable cassette format.
- Tests for each architecture layer.
- No live network calls in tests.
- No secrets committed.
- Simple CLI UX when CLI work begins.
- Documented limitations.
- CI-ready design.
- Safe defaults.
- Clear module boundaries.
- Honest roadmap.

## Definition of Done for Each Step

A step is done when:

- The approved scope is implemented and no more.
- Relevant tests are added or updated.
- Tests pass, unless the step is documentation-only and no code behavior changed.
- `PROJECT_STATUS.md` is updated.
- `DEVELOPMENT_LOG.md` is updated.
- `ARCHITECTURE_DECISIONS.md` is updated if a major decision changed.
- The work has been checked against `QUALITY_CHECKLIST.md`.
- Runtime behavior remains offline unless live behavior was explicitly approved.
- The final summary lists files changed, tests run, result, and next step.

## Definition of Done for MVP

The MVP is done when agentrec can:

- Record an offline agent run.
- Replay that run hermetically from cassette data.
- Fail loudly on replay cache misses.
- Show a run trace in the terminal.
- Diff two runs by tool sequence, final output, cost, latency, and step changes.
- Support tests that run without live APIs or network calls.
- Store cassettes in an inspectable local filesystem format.
- Demonstrate the full flow with a fake provider and calculator tool.

## What Would Make This Look Like a Weak College Project

- Broad claims not backed by code.
- No tests.
- Hidden live API calls.
- Unclear errors.
- Giant unstructured files.
- Dashboard before core engine.
- Fake "AI" features without infrastructure depth.
- Fragile demos that only work once.
- Unclear cassette data.
- No documented limitations.

## What Would Make This Look Production-Grade

- Focused architecture.
- Real replay guarantees.
- Clean cassettes.
- Strong tests.
- Readable docs.
- Honest roadmap.
- CI workflow before GitHub push.
- Clear errors.
- Offline-first MVP.
- Safe handling of secrets and generated run data.
- Small modules that can be reviewed and trusted.
