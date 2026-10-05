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
