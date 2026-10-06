# Cassette schema v2

A cassette is a directory with exactly two required files:

- `cassette.json`: ownership marker `agentrec_cassette="agentrec"`,
  `schema_version=2`, package and matching-policy versions, redaction-policy
  version, status, creation/finalization times, interaction count, SHA-256 of
  `interactions.jsonl`, and an optional failed-run error.
- `interactions.jsonl`: one JSON object per completed HTTP or tool boundary,
  in contiguous `seq` order. Each has a SHA-256 match key, zero-based
  per-key `occurrence`, request, exactly one response or error, start time,
  duration, and `key_inputs_redacted`.

HTTP requests contain method, URL, headers, body, and body encoding
(`text` or `base64`). HTTP responses also contain status and `streamed`.
Tool requests contain name and arguments; tool responses contain result.
Unknown fields and wrong primitive types are rejected.

`structural` validation parses both files and checks strict models and
contiguous sequence. `integrity` adds digest/count checks, per-key occurrence
checks, and key recomputation where possible. `replayable` requires a complete
status by default and an outcome for every interaction. `privacy` adds scans
for built-in secret patterns. The CLI defaults to privacy, which includes the
earlier levels.

If redaction changes a key input, the cassette sets
`key_inputs_redacted=true`. Integrity reports that key as unverifiable
rather than pretending it can recompute the original hash. The SHA-256 digest
detects accidental edits when metadata is unchanged; it is not a signature or
protection against an attacker who can rewrite both files. Review untrusted
cassettes before using them. Schema v1 is rejected; see [migration](migration.md).

Tool arguments and results encode non-finite floats as single-key `$float`
objects with `inf`, `-inf`, or `nan` values. Literal single-key `$float` and
`$object` dictionaries are escaped as `$object` pairs to prevent collisions.
Replay decodes these tags before returning tool results; integrity validation
decodes arguments before recomputing their key. HTTP binary bodies use
`body_encoding: base64`; HTTP text is UTF-8. Responses store decoded bytes
and omit stale content-encoding and content-length headers. The HTTP client
may generate a new content-length matching the decoded body.

Streaming replay preserves decoded body bytes and parsed events, not original
chunk sizes or timing. A midstream transport error is replayed as an error
before any response chunks; partial output before the original error is not
reproduced. Early closing a recorded stream drains it, which can block until the
upstream ends or times out. Cancellation and process termination are not resumable
recordings. Finish calls/streams before closing a session.

Trajectory diff compares stored requests/outcomes, not final application state
outside these boundaries. It aligns by seq for equal lengths and key/occurrence
when lengths differ. Details show at most ten differing paths per field and
truncate rendered values to 100 characters; the changed-step count still signals
a difference. Metadata and timestamps are not behavioral changes.
