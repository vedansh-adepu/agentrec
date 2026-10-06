# Security

Report sensitive issues privately through the repository's GitHub security advisory
form: https://github.com/vedansh-adepu/agentrec/security/advisories/new.
Do not put real credentials or private cassettes into a public issue.

Redaction runs before persistence and recognizes configured header/query names and
known token patterns. It reduces accidental disclosure; it cannot recognize every
secret or all PII. Email and entropy detection are off by default. Binary/base64
bodies, arbitrary passwords, encoded secrets, and unrecognized sensitive fields require
application review/custom hooks. Hooks receive unredacted values in memory.

Cassettes can contain prompts, tool arguments/results, model output, URLs, and error
messages. Review them before committing or sharing. Scrub older recordings after
adding rules; redaction does not remove copies already committed to Git history.

Treat untrusted cassettes as untrusted input. Strict schema checks and path
containment reduce malformed-input hazards; hashes are not authenticity signatures.
A writable attacker can edit both data and metadata, including unverifiable-key
flags. Recording/replay is not a process sandbox. Code outside supplied transports
and decorators can access the network/filesystem, and fixture payloads may still
influence application behavior. Bound input size in applications handling hostile
files; the loader and streams buffer data in memory.
