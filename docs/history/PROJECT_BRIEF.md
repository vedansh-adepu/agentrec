Historical code blocks are illustrative records of the original 0.x project; they are not current commands.

# agentrec Project Brief

## What agentrec is

agentrec is a deterministic record-and-replay harness for AI-agent runs.

It records every model call and tool call an AI agent makes, stores those interactions as content-addressed cassettes, and replays them later without calling live models, APIs, networks, or real tools.

The product sentence:

> agentrec records every model and tool call an AI agent makes, stores the interactions as content-addressed cassettes, and replays them hermetically so agent runs become reproducible, testable, and diffable.

## Why AI-agent runs are hard to test

AI-agent runs are difficult to test because they often depend on things that change between runs:

- model output can vary
- tool output can vary
- network calls can fail or return different data
- prompts and intermediate steps can drift
- API latency and cost can change
- agent loops can take different paths

A normal unit test expects the same input to produce the same output. Agent systems often do not behave that way unless every model and tool interaction is controlled.

agentrec exists to make those interactions reproducible.

## Core goal

The MVP should prove this workflow:

1. `record`: run an agent once and capture every model and tool interaction
2. `replay`: run it again using only cached responses
3. `show`: inspect what happened during a run
4. `diff`: compare two runs
5. `test`: use replayed runs in automated tests

This is not just a logger. A logger tells you what happened. agentrec should let you reproduce what happened.

## Hermetic replay

Hermetic replay means replay mode is sealed off from the outside world.

During replay, agentrec must not silently call:

- live model APIs
- live tools
- network services
- real external systems

If the replay cache does not contain the needed response, replay must fail loudly. In later phases, that failure should be a `ReplayMissError`.

The rule is simple: replay either uses the cassette, or it fails.

## What a cassette is

A cassette is the stored set of recorded interactions for a run.

For agentrec, a cassette should contain model requests, model responses, tool calls, tool results, usage, timing, and enough metadata to understand what happened.

The cassette should be content-addressed where possible. That means a request can be normalized, hashed, and used to look up the recorded response for that exact request.

## What a trace is

A trace is the ordered story of a run.

It should describe the sequence of steps an agent took, such as:

- model request
- model response
- tool call
- tool result
- final output

The trace is useful for display, debugging, validation, and diffing.

## What a request hash is

A request hash is a SHA-256 digest created from a normalized request.

Normalization removes fields that should not matter, such as timestamps and request IDs, while preserving meaningful fields such as the model, messages, tool names, and tool arguments.

The same meaningful request should always produce the same hash. Meaningfully different requests should produce different hashes.

## MVP scope

The MVP should stay small:

- Python 3.11+
- Typer CLI
- Pydantic models
- Rich terminal output
- pytest tests
- local filesystem cassette store
- fake model provider only
- simple tool registry
- calculator tool

The first implementation step only includes:

- project configuration
- package skeleton
- Pydantic models
- request normalizer
- SHA-256 request hasher
- basic tests for hashing and serialization

## Planned commands

Planned commands for later phases:

```bash
agentrec record --task "<task>" --agent examples.math_agent:run --out runs/math_001
agentrec replay runs/math_001
agentrec show runs/math_001
agentrec diff runs/math_001 runs/math_002
agentrec validate runs/math_001
```

These commands should not be implemented in Step 1.

## Planned architecture

The planned architecture should grow in small layers:

- `models`: typed records for runs, steps, usage, and cached interactions
- `normalizer`: stable request normalization before hashing
- `hashing`: content hashes for request lookup
- `cassette store`: local filesystem storage for recorded interactions
- `providers`: fake/offline model provider first
- `tools`: simple tool registry and calculator tool
- `recorder`: captures model and tool interactions
- `replayer`: serves cached interactions and rejects misses
- `cli`: Typer commands for record, replay, show, diff, and validate
- `diff`: compares run traces, final output, costs, latency, and step changes

## Production-level success

agentrec is successful at production level when:

- replay mode is hermetic
- replay misses fail loudly
- cassettes are deterministic and easy to inspect
- tests can run without live APIs
- run diffs clearly show behavior changes
- cost and latency changes are visible
- developers can trust recorded runs as regression fixtures
- the project remains small enough to understand

## Testing requirements

Tests should prove behavior, not implementation details.

Important testing areas:

- stable request hashing
- request normalization
- model serialization
- cassette read/write behavior
- replay cache hit behavior
- replay miss behavior
- no live calls during replay
- CLI command behavior
- run diff behavior

Step 1 tests only cover stable hashing and model serialization.

## Non-goals

Do not build these yet:

- web dashboard
- live OpenAI provider
- live Anthropic provider
- complex agent framework integrations
- distributed storage
- tracing SaaS backend
- plugin system
- large tool ecosystem
- automatic prompt optimization

## Future roadmap

Likely future steps:

1. local cassette store
2. fake model provider
3. tool registry
4. calculator tool
5. recorder
6. hermetic replayer
7. Typer CLI
8. show command with Rich output
9. diff engine
10. validation command
11. example math agent
12. pytest fixtures for replayed agent tests
13. optional live provider integrations after the offline MVP is proven

## GitHub push plan

Suggested GitHub flow:

1. create the project foundation
2. run tests locally
3. initialize a clean first commit
4. create a GitHub repository
5. push the initial branch
6. continue with one small feature branch per implementation step

Do not commit secrets, API keys, `.env` files, or generated private runs.
