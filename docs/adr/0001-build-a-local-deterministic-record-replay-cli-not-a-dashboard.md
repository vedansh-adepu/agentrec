# ADR-0001: Build a Local Deterministic Record/Replay CLI, Not a Dashboard

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


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
