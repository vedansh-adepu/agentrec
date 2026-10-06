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

## Windows readiness

`.gitattributes` forces LF for JSON, JSONL, Python, YAML and Markdown. Golden
cassette integrity hashes the exact JSONL bytes, and the tests check both that
digest and Git's checkout attributes. Filesystem-writing tests use `tmp_path`;
absolute-looking paths in malformed payload tests are rejected input strings.
Symlink tests skip with a capability reason only when Windows cannot create the
link. The case-alias lock test skips on case-sensitive filesystems.

Storage tests cover a transient sharing violation, a persistent replacement
failure, closed write handles before replacement, interrupted-write temporary
cleanup, interrupted lock cleanup and Windows directory-fsync omission.
Catchable interruptions run cleanup; process termination or power loss can
leave temporary files or a stale lock. Inspect those before removing them;
agentrec does not automatically steal stale locks.

On Windows, asyncio needs a TCP socketpair for local IPC. The test fixture
constructs only a fixed loopback pair using the pre-guard socket constructor;
it does not enable ordinary sockets or DNS. Its helper is tested with fake
sockets. Actual Windows behavior still needs the remote matrix.

The release workflow has only a `push.tags: ["v*"]` trigger. A branch push or
pull request cannot start it. Publication additionally requires
`PYPI_PUBLISH_ENABLED == 'true'` and uses the `pypi` environment. Required
reviewers must be configured in repository settings; naming the environment
in YAML does not prove that protection has been configured.
