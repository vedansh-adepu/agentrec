# ADR 0015: Redaction before persistence

## Context

Agent calls may contain credentials or personal data in headers, query strings,
tool arguments, and model responses.

## Decision

The session applies default header/query rules and value scanning in memory
before adding each interaction to the write buffer. A cassette can be scrubbed
later as rules evolve, and privacy validation searches parsed values.

## Consequences

Default rules reduce accidental disclosure but cannot guarantee detection of
every secret. Matching still uses the original request in memory; secret body
values can change a key unless that path is explicitly ignored. Redacted
request fields limit later integrity recomputation and are marked as such.
