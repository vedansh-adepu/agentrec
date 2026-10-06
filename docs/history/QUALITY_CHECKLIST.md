# agentrec Quality Checklist

Apply this checklist before approving every implementation or documentation step.

## Scope Control

- Did the step stay within the approved scope?
- Did the change avoid implementing future-step behavior early?
- Did the change avoid dashboards, live providers, cloud services, databases, or unrelated infrastructure?
- Did the change preserve the core record/replay guarantee?

## Architecture

- Is the module boundary clear?
- Does the change fit the current architecture layers?
- Are abstractions small and justified?
- Are files small and understandable?
- Is the cassette format still inspectable?

## Tests

- Were relevant tests added or updated?
- Do all tests pass?
- Do tests use deterministic inputs?
- Do tests avoid real network/API calls?
- Do tests avoid real `runs/` data and use temporary paths where appropriate?

## Replay Safety

- Does replay remain planned as hermetic?
- Are there any silent live fallbacks?
- Would a missing cached response eventually be able to raise `ReplayMissError`?
- Are model/tool calls separable enough for record and replay behavior?

## Storage/Data Safety

- Is generated private run data ignored by Git?
- Are cassette files written in a simple, inspectable format?
- Are required files validated where appropriate?
- Are meaningful request fields preserved during normalization?

## Error Handling

- Are errors clear and typed?
- Are missing files or missing cached interactions reported loudly?
- Are invalid inputs rejected clearly?
- Are exceptions specific enough for future CLI output?

## Code Quality

- Are models typed?
- Are functions/classes focused?
- Is the implementation deterministic where expected?
- Is unsafe behavior avoided?
- Are comments used only where they clarify non-obvious code?

## Documentation Updates

- Is `PROJECT_STATUS.md` updated?
- Is `DEVELOPMENT_LOG.md` updated?
- Was `ARCHITECTURE_DECISIONS.md` updated if a major decision changed?
- Are limitations and next steps stated honestly?

## Git Hygiene

- Are generated files excluded?
- Are secrets, API keys, `.env` files, and private runs avoided?
- Are unrelated files left untouched?
- Are changes easy to review by file?
- Are `Co-Authored-By` trailers avoided?

## Security/Privacy

- Are there any real network/API calls?
- Are secrets avoided?
- Are unsafe evaluation paths avoided?
- Is user/private run data kept out of version control?
- Are defaults safe for local development and testing?
