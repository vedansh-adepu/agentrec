# ADR 0011: Per-key occurrence queues

## Context

The v0 response store used a single file per request hash. A repeated identical
request overwrote the earlier response.

## Decision

Schema-v2 replay indexes interactions by key and consumes each key's
occurrences in recorded order. Global sequence order is optional. Replay
accounts for unused and repeated calls.

## Consequences

SDK retries and flaky tools can return distinct recorded outcomes for the same
request. Default replay permits different interleavings across independent
keys; strict order is available for single-threaded trajectories. A request
beyond the recorded count fails unless playback repeats are explicitly enabled.
