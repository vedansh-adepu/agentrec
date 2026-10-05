# Test quality

Tests block Internet sockets and use fake upstream transports. Unix sockets
remain allowed for local asyncio event loops. Generated tests use fixed bounds,
no Hypothesis database, and no deadline so timing does not create failures.

## Mutation measurements

Measured with Python 3.13.2 and mutmut 3.8.0 on macOS 26.6.2 ARM64.
Run `make mutation` from an environment with the dev and test extras installed.
The runner creates a temporary source copy and prints its location; the original
checkout is never mutated. Results remain in that temporary directory for review.

| Module | Mutants | Killed | Survived | Raw score |
| --- | ---: | ---: | ---: | ---: |
| canonical.py | 267 | 215 | 52 | 80.52% |
| matching.py | 248 | 219 | 29 | 88.31% |
| cassette/replay.py | 141 | 125 | 16 | 88.65% |

No mutants timed out, were suspicious, or lacked a test. Scores include all
mutants, including equivalent ones; none were manually excluded. The 85% target
is **not met for canonical.py**. Reviewed survivors include error-message
capitalization and equivalent `float("INF")`/`float("inf")` values, as well as
remaining malformed-tag branch gaps. This is not a claim that every survivor
is harmless. Further canonical malformed-input testing is a known follow-up.

Mutation review added tests for JSON-pointer escaping and array boundaries,
invalid tags, exact wire encoding, all HTTP key components, golden policy-v1
keys, and strict replay accounting. These protect actual persisted-format and
replay behavior rather than merely raising the score.

## Fuzzing

`tests/test_loader_fuzz.py` generates 150 bounded malformed metadata/interaction
examples and checks that loading either succeeds or raises an agentrec error,
with every file byte unchanged. Explicit cases cover 20,000 nested containers,
5,000-digit integers, invalid UTF-8, and hostile interaction keys. This is
bounded property testing, not an exhaustive proof or a resource-exhaustion sandbox.

## Dependency and platform checks

The lowest-direct job uses Python 3.11 and `uv pip install --resolution
lowest-direct -e ".[test,httpx,pytest]"`. Direct bounds were checked locally on
Python 3.11.5: pydantic 2.7.0, typer 0.21.0, rich 13.7.0, httpx2 2.13.0,
httpx 0.27.0, OpenAI 3.0.0, Anthropic 1.0.0, pytest 8.0.0, and Hypothesis 6.100.0.
Transitive dependencies resolve normally; this does not test every version combination.
Older OpenAI SDK releases may wrap replay errors in APIConnectionError; inspect
`__cause__`. The demo handles both direct and wrapped errors.

The matrix is configured for Ubuntu, macOS, and Windows with Python 3.11/3.12/3.13.
Only local macOS Python 3.11 and 3.13 were executed during development; remote
matrix success must be checked after the branch is published. Windows storage
behavior is also simulated by tests for one PermissionError retry and omitted
directory fsync. Simulations do not substitute for an actual Windows runner.
