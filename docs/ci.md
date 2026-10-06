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

The published branch passed all nine OS/Python jobs, lowest dependencies,
quality/docs, packaging/wheel smoke and pip-audit in this
[verified tests run](https://github.com/vedansh-adepu/agentrec/actions/runs/37408832197).
[CodeQL](https://github.com/vedansh-adepu/agentrec/actions/runs/37408832273)
also passed. Release and Pages deployment were not triggered. Publishing and
Pages setup are described in [releasing](releasing.md).

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
sockets. All three Windows matrix jobs passed in the linked tests run.

The release workflow has only a `push.tags: ["v*"]` trigger. A branch push or
pull request cannot start it. Publication additionally requires
`PYPI_PUBLISH_ENABLED == 'true'` and uses the `pypi` environment. Required
reviewers must be configured in repository settings; naming the environment
in YAML does not prove that protection has been configured.

## Manual live verification

`scripts/live_smoke.py` is a manual, paid-provider check and is never invoked
by CI. Install `agentrec[test]` in your environment, set `OPENAI_API_KEY`
and/or `ANTHROPIC_API_KEY`, then pass an explicit small, inexpensive model you
have access to for each configured provider (illustrative, not executed here):

```bash
python scripts/live_smoke.py --openai-model "$OPENAI_SMOKE_MODEL" --anthropic-model "$ANTHROPIC_SMOKE_MODEL"
```

Omit the flag for a provider whose key is absent; that provider is skipped.
There are no model defaults. OpenAI uses Chat Completions, so select a model
supporting that endpoint and `max_completion_tokens`. Anthropic uses Messages.
`--max-tokens` defaults to 32 and must be positive; this is an output-token
limit, not a cost guarantee. SDK retries are disabled.

The default output is a new system-temporary `agentrec-live-smoke-*` directory
outside the repository. `--output /path/outside/repo` selects a location;
existing provider subdirectories are refused. Writing inside the repository
requires `--allow-repo-path`. The default name pattern is ignored by Git, but
custom names are your responsibility. Keep cassettes private and inspect them:
redaction is best effort, and this script does not delete its output.

Each active provider records one non-streaming and one streaming request via
`rec.transport()`, repeats both in sealed `none` mode, compares parsed SDK
objects/events and checks exactly two recording calls and zero replay upstream
calls. It invokes the actual CLI twice, with `validate --level replayable`
and `validate --privacy`, and prints both JSON results. Response redaction can
change returned values and make the parsed equality assertion fail; inspect
such a failure locally. Errors print their type, not SDK request details.

Live smoke verified against OpenAI gpt-4.1-nano (streaming + non-streaming) on 2026-10-06; Anthropic not yet verified

The manual run recorded two upstream calls (one streaming, one non-streaming),
then replayed identical parsed SDK results with zero upstream calls. Both
`validate --level replayable` and `validate --privacy` passed; a count-only scan
of all new cassette files found zero `sk-` occurrences. The key was read inline
from macOS Keychain, never printed or committed, and all temporary cassettes were
removed after inspection. This verifies this model/run, not all provider versions
or streaming timing. Offline tests continue to use synthetic inputs and fake
upstreams; no live-provider check is added to CI.
