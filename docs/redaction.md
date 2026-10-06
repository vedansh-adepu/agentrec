# Redaction

Sessions redact requests, responses, tool arguments, tool results, and failure
messages before they enter the cassette write buffer. Default header names are
`authorization`, `x-api-key`, `api-key`, `openai-organization`, `cookie`, and
`set-cookie`. Query names matching `api_key|key|token|secret` are redacted.
Stored strings are scanned for OpenAI and Anthropic keys, AWS access key IDs,
GitHub and Slack tokens, JWTs, bearer tokens, and PEM private keys. Replacements
use `[REDACTED:<rule>]`.

Redaction policy version 2 also recognizes provider key echoes with asterisk-masked
middles, including visible prefixes/suffixes in authentication-error bodies and
session error metadata. The same patterns apply to requests, responses and headers,
and to `validate --privacy` and `scrub`. Older policy-version-1 cassettes remain
readable, but masked echoes may survive in them; review or scrub those private
recordings before sharing. Recognition is best effort and does not validate a key.

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
recover secrets already published elsewhere. The CLI provides `scrub` and `validate --privacy` for these checks.

Known patterns are scanned in object keys as well as string values. If redaction
would collapse two distinct keys into one, recording fails rather than losing a
field. Application hooks are still necessary for binary/encoded data and unknown
secret formats. Privacy findings do not expose secret keys in diagnostic paths.

Replay returns stored, redacted responses and tool results. Those can differ
from the original live outputs. If sanitized values flow into later requests,
configure matching ignore paths deliberately; the recorder cannot recover the
redacted originals from disk. Tests explicitly replay sanitized HTTP/tool values.
