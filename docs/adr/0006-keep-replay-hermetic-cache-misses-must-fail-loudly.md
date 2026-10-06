# ADR-0006: Keep Replay Hermetic; Cache Misses Must Fail Loudly

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


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
