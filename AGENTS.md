# Repository instructions

agentrec is a Python record/replay harness for AI-agent runs. Work on the
`v1-production` branch, in the phase order of the v1.0.0rc1 brief. Keep
changes small, typed, tested, and documented. Commit each completed phase
only after the full test suite passes.

Replay must never silently call a live network or execute a recorded tool.
Tests use fake upstreams and block sockets. Never commit secrets, API keys,
private cassettes, or generated run data. Do not push, merge, release, or
open a pull request without a new user instruction.

The original development notes are preserved in `docs/history/`; the
architecture decisions are in `docs/adr/`.
