# ADR 0012: Explicit JSON-pointer matching

## Context

The v0 normalizer removed keys such as `timestamp` at every nesting level. A
tool argument can use such a key as meaningful data, so this made different
requests match.

## Decision

The v1 matching policy preserves every body field by default. Callers may
ignore named JSON-pointer paths and query parameters explicitly. The policy
name, version, and configuration contribute to every key.

## Consequences

Default matching is conservative. Volatile values require deliberate
configuration; a policy change produces different keys. The canonical
encoder preserves integer/float distinctions and tags non-finite floats.
