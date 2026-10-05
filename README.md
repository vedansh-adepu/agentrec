# agentrec

Deterministic record/replay for AI-agent runs: model calls and tool calls, in
order, offline.

[![CI](https://github.com/vedansh-adepu/agentrec/actions/workflows/tests.yml/badge.svg)](https://github.com/vedansh-adepu/agentrec/actions/workflows/tests.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Why I built it

Agent failures are hard to reproduce: the same request can return different
answers, tools can be flaky, and a bug you cannot replay is hard to fix. I
wanted each failure to become a deterministic test fixture. agentrec records
HTTP model calls and Python tool boundaries into one ordered cassette, then
replays their recorded outcomes.

## Install

From a clone, create a virtual environment and install the test extras.
`httpx2` is installed with the test extra; the optional legacy adapter is
`agentrec[httpx]`. The current branch is development work toward 1.0.0rc1,
not a published release.

## Quickstart

The [field-tech example](examples/field_tech_agent/run.py) is executable
source for an OpenAI SDK client with a fake upstream, a session transport, and
three decorated tools. It requires no account or network access. Applications
using a real provider pass an SDK client backed by `rec.transport()` or
`rec.async_transport()`; they must supply their own credentials and policy.

## The 60-second demo

With the project installed using `pip install -e ".[test]"`, run
`python examples/field_tech_agent/run.py`. The test suite executes the same
demo and checks its output. Actual output from that command:

```text
record: Replace the IGN-9 igniter on furnace F-100. model_calls=3 work_order=True
replay: Replace the IGN-9 igniter on furnace F-100. upstream_calls=0 work_order=False
modified prompt: replay miss for POST https://offline.example.test/v1/chat/completions; closest recorded: seq 0 first differing path /body; seq 3 first differing path /body; seq 6 first differing path /body
diff: steps=7 changed=2 added=0 removed=0
```

The cassette contains three model calls with the same key and two
`search_parts` calls with the same key. Replay consumes each occurrence in
order and does not run the `create_work_order` body.

## Guarantees and limits

| Behavior | Guarantee |
| --- | --- |
| Replay miss | Raises instead of calling the upstream transport or tool body. |
| Repeated key | Consumes recorded occurrences in order; an extra call fails. |
| Tool effects | Recorded result or exception replays, but side effects do not. |
| Validation | Checks schema, digest, counts, keys where recomputable, status, and known secret patterns. |
| Concurrency | Recorded `seq` is completion order; global strict-order replay is optional. |
| Isolation | This is a boundary recorder, not a process sandbox. Code outside the supplied transport/decorators can perform effects. |

## Record modes

| Mode | Behavior |
| --- | --- |
| `none` | Replay only. Misses fail. |
| `once` | Record if absent; replay if present. |
| `new_episodes` | Replay matches and record misses. |
| `all` | Replace an owned cassette with a new recording. |

`AGENTREC_MODE` overrides a session's unspecified mode. The pytest fixture
uses `none` by default in CI and `once` locally.

## Matching

Default HTTP keys include method, normalized scheme/host/port/path, sorted
query parameters, and a canonical JSON body or raw-byte hash. Headers are
excluded unless explicitly selected. Tool keys include the tool name and
canonical arguments. `MatchPolicy(ignore_body_paths=("/metadata/request_id",))`
ignores only that JSON-pointer path; meaningful nested `timestamp` values
remain. Policy identity and configuration are stored in the cassette.

## Redaction

Default rules redact sensitive header and query values and scan all stored
strings for common key and token patterns. Matching uses the original request
in memory; redaction happens before cassette writes. Secret values in a body
still affect the key unless their path is explicitly ignored. Run
`agentrec scrub CASSETTE` to apply current rules to an older cassette and
`agentrec validate CASSETTE --privacy` to scan for known patterns. These
rules reduce accidental disclosure, but cannot guarantee every secret is
recognized. See [redaction](docs/redaction.md).

## Validation and diff

`agentrec validate CASSETTE` defaults to replayability and privacy checks.
`--level structural|integrity|replayable|privacy` selects a cumulative level.
`agentrec diff A B --json --fail-on-change` reports changed request,
response, and error paths plus added or removed steps; duration changes are
reported separately from behavior. Check commands exit 1 on failed checks;
invalid input exits 2. See [cassette format](docs/cassette-format.md) and
[CI/pytest](docs/ci.md).

## Cassette format

Schema v2 uses `cassette.json` and `interactions.jsonl`. The old schema-v1
layout is rejected; see [migration](docs/migration.md). The interaction file
and metadata file are each replaced atomically, with metadata last. A crash
between replacements is detectable by the digest, but two files are not one
filesystem transaction.

## How it compares

HTTP cassette libraries and LLM-focused replay tools already exist.
agentrec's focus is model and tool boundaries in one ordered cassette,
occurrence-correct replay, pre-persistence redaction, and step-level trajectory
diffs through HTTPX2-native transports. It does not claim to be the first or
the broadest recorder.

## Limitations

This branch has not been published to PyPI. The legacy v0 math API remains in
the source tree temporarily, while its CLI commands have been removed.
Current tests use fake upstreams, not live OpenAI or Anthropic API calls.
Redaction cannot prove all sensitive content is absent. The format digest is
not an authenticity signature. Benchmark and release hardening are still in
progress.

## Roadmap

Finish real-traffic edge cases, broader fuzz/property testing, performance
measurement, strict package-wide typing and linting, documentation site, and
release/supply-chain workflows before tagging 1.0.0rc1.

## License

MIT. See [LICENSE](LICENSE).
