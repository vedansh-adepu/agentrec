# ADR 0016: Schema v2 and v1 rejection

## Context

The v1 cassette layout has per-key response files and cannot represent repeated
requests with distinct outcomes.

## Decision

Schema v2 uses an ordered `interactions.jsonl` plus `cassette.json` with an
ownership marker, policy identity, count, status, and SHA-256 content digest.
The v1 loader rejects the old layout with a migration instruction.

## Consequences

A new cassette is required for v1 recordings. The two files are each replaced
atomically, with metadata written last; an interruption between replacements is
detectable through the content digest. A two-file update is not a single
filesystem transaction.
