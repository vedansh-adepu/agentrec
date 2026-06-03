# Repository Instructions for Codex

This repository is for agentrec, a deterministic record-and-replay harness for AI-agent runs.

Work one step at a time. Explain what you are about to change before editing files.

Before each new step, read:

- `PROJECT_BRIEF.md`
- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`
- `ARCHITECTURE_DECISIONS.md`
- `QUALITY_CHECKLIST.md`
- `PRODUCTION_STANDARDS.md`

Keep changes small, typed, and testable. Prefer simple code over clever abstractions.

Do not overbuild. The MVP should prove record -> replay -> show -> diff -> test.

Do not drift beyond the approved step.

Keep all work one step at a time.

Do not interpret production-level as adding unnecessary infrastructure. No dashboard, Docker, database, cloud sync, auth, or live providers until the core offline MVP is correct.

Do not add live OpenAI or Anthropic providers yet. Start with fake/offline behavior only.

Do not build a web dashboard.

Replay mode must remain hermetic. It must never silently call live APIs, live models, networks, or real tools.

In later phases, a missing cached response must raise `ReplayMissError`.

Never commit secrets, API keys, `.env` files, or generated private runs.

Do not add `Co-Authored-By` trailers to commits.

After each completed step, update:

- `PROJECT_STATUS.md`
- `DEVELOPMENT_LOG.md`

Update `PROJECT_STATUS.md` with files changed, tests run, current status, and next step.

Update `ARCHITECTURE_DECISIONS.md` only when a major design decision is introduced or changed.

Before asking for step approval, check work against `QUALITY_CHECKLIST.md` and `PRODUCTION_STANDARDS.md`.

After each step, summarize changed files and tests run.
