# Errors

Library errors expose `code`, `message`, and `hint`. Their string form has a
single message line followed by a `hint:` line. The CLI prints the first line
and uses `--debug` to preserve the traceback. Codes are stable across 1.x.

| Code | Exception |
| --- | --- |
| AR000 | AgentRecError |
| AR200 | CassetteError |
| AR201 | CassetteNotFoundError |
| AR202 | CassetteValidationError |
| AR101 | ReplayMissError |
| AR102 | ReplayExhaustedError |
| AR103 | ReplayOrderError |
| AR104 | UnplayedInteractionsError |
| AR105 | ReplayedToolError |
| AR106 | ReplayedTransportError |
| AR203 | CassetteStoreError |
| AR204 | CassetteVersionError |
| AR205 | CassetteOwnershipError |
| AR206 | CassetteLockedError |
| AR301 | CanonicalValueError |
| AR302 | MatchPolicyError |

Known recorded HTTP exceptions retain the SDK transport exception type.
Recorded tool exceptions use `ReplayedToolError` with `original_type` and
`original_message`. Python usage errors and optional dependency import errors
retain their standard Python types.

The `agentrec` logger reports keys and decisions at DEBUG and body sizes at
WARNING. It never logs body contents, URLs, headers, or tool arguments.
The body warning threshold defaults to 5 MiB (`max_body_bytes`); bodies are
never truncated. Streaming bodies are measured when consumption finishes.
