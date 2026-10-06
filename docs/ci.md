# Offline tests and pytest plugin

The test suite uses `pytest-socket` with network sockets disabled. Local Unix
socketpairs remain available because asyncio needs them for its event loop.
All SDK integration tests use fake HTTP transports and no API credentials.

The optional `agentrec[pytest]` extra registers the `agentrec_session` fixture
and `@pytest.mark.agentrec(cassette="name")` marker. The fixture stores a
cassette under `tests/cassettes/`; without an explicit name it derives a safe,
stable name from the test node ID. Run with `--agentrec-mode=none` for sealed
replay, or `once`, `new_episodes`, and `all` when deliberately recording.

The mode precedence is the CLI option, then `AGENTREC_MODE`, then the default.
The default is `none` when `CI` is set and `once` otherwise. A replay miss
never reaches the fake or live upstream. Keep private cassettes out of Git and
review any cassette before committing it.

CI starts `coverage run -m pytest` before pytest plugins import agentrec, then
requires both a 90% overall branch-enabled report and 90% branch-only coverage
from coverage.py JSON totals. Starting coverage only after
pytest11 imports would miss import-time code. The matrix covers three Python
versions on three OSes; quality checks run ruff, strict mypy, and strict MkDocs.
Packaging builds wheel/sdist and tests the installed wheel in a fresh venv with
core dependencies only. pip-audit is a non-blocking warning job. CodeQL and
Scorecard upload findings to code scanning. No Scorecard badge is shown before
a successful remote run. All external actions use full verified commit SHAs.

These workflows are configured, not remotely verified in this local branch.
Publishing and Pages setup are described in [releasing](releasing.md).
