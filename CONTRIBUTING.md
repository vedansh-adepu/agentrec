# Contributing

Use Python 3.11+ and uv. Illustrative setup/check commands:

```bash
uv venv
uv pip install -e ".[dev,test,httpx,pytest]"
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src
uv run pytest --cov=agentrec --cov-branch --cov-report=term-missing
uv run mkdocs build --strict
```

Tests must remain offline: use fake upstream transports and the global socket
blocker. For behavioral changes, add a regression demonstrating the failure first.
Use small commits named `type(scope): summary`; do not rewrite existing history.
Run `make mutation` optionally from the activated venv; see docs/test-quality.md.

To add a redaction rule, add a named compiled regex to BUILTIN_PATTERNS, a positive
and negative regression, and a generated-pattern invariant. Verify replacements do
not themselves match built-in rules. Document false positives and review stored
payloads. Keep private cassettes and actual credentials out of tests and issues.

uv.lock pins contributor tooling; package metadata keeps flexible lower bounds for
library users. The lowest-direct CI job tests those bounds separately from the
contributor lock. GitHub matrix results must be checked after publishing a branch.
