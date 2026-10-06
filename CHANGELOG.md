# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0rc1] - Unreleased

### Changed

- Breaking: cassette schema v2 replaces the old multi-file schema; v1 requires re-recording.
- Breaking: fake math record/replay CLI commands are removed; the offline demo lives in examples.
- Breaking: old 0.x Python imports move to private `_legacy`; use the Session API.
- Public Session API records HTTP SDK clients and decorated sync/async tools.

### Fixed

- A1: repeated requests consume FIFO occurrences; extra calls fail.
- A2: meaningful nested timestamp/ID fields remain; ignores use explicit JSON pointers.
- A3: validation checks typed outcomes, digest, requests, counts, occurrences, and completion status.
- A4: existing session cassettes get integrity checks; inspection commands get structural checks.
- A5: diff includes requests, tool arguments, intermediate responses, and errors.
- A6: replacement/scrub refuse unowned directories and avoid delete-then-write.
- A7: record modes prevent silent reuse/corruption of existing cassettes.
- A8: buffered atomic finalize records failed runs and boundary errors.
- A9: inf, -inf, and nan round-trip with collision-safe tags.
- A10: tool arguments are snapshotted before mutable tool execution.
- A11: expected CLI errors have concise messages and documented exit codes.
- A12: keys and cassette filenames cannot traverse outside their directory.
- A13: configured secret redaction occurs before persistence; privacy validation and scrub added.
- A14: README contradictions and broken math-demo ordering replaced by an executed real SDK demo.

### Added

- HTTPX2 and optional legacy HTTPX transports, progressive SSE recording, retries and binary bodies.
- Per-key replay accounting, optional strict global order, explicit matching policies and record modes.
- pytest fixture/marker and CI replay defaults; stable error codes, hints, and private-value-safe logs.
- Offline official SDK integrations, generated invariants, loader fuzzing, mutation measurements,
  Windows atomic-write checks, minimum-dependency tests, and measured performance benchmarks.
- Documentation site, security guidance, API stability policy, and contributor instructions.
