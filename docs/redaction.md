# Redaction

Sessions redact requests, responses, tool arguments, tool results, and failure
messages before they enter the cassette write buffer. Default header names are
`authorization`, `x-api-key`, `api-key`, `openai-organization`, `cookie`, and
`set-cookie`. Query names matching `api_key|key|token|secret` are redacted.
Stored strings are scanned for OpenAI and Anthropic keys, AWS access key IDs,
GitHub and Slack tokens, JWTs, bearer tokens, and PEM private keys. Replacements
use `[REDACTED:<rule>]`.

Email redaction and high-entropy scanning are opt-in because they can mask
ordinary data. A `Redactor` can add named regex rules and in-memory
`before_record_request`, `before_record_response`, and `before_record_tool`
callbacks. These callbacks run before redaction and must return a dictionary.
They should not write unredacted data elsewhere.

Matching hashes the original request in memory. Headers are excluded from the
default match key, so changing an authorization header does not cause a miss.
A secret in the body or a non-ignored query parameter changes the key; use an
explicit matching-policy ignore path when that value is deliberately volatile.
The cassette marks interactions whose stored request cannot reproduce the
original key with `key_inputs_redacted=true`.

Redaction reduces accidental disclosure; it cannot prove that every secret is
recognized. Review cassettes before committing them. `scrub(path, redactor)`
reapplies current rules to an owned cassette and updates its digest. It cannot
recover secrets already published elsewhere. The CLI scrub and privacy
validation commands are added in later phases.
