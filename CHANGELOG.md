# Changelog

All notable changes to this project will be documented here. This file
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Schema-v2 record/replay sessions for HTTPX2-based OpenAI and Anthropic SDK
  clients, including async calls, tool boundaries, occurrence queues,
  redaction, validation levels, and trajectory diffs.
- `show`, `diff`, `validate`, `scrub`, `inspect-miss`, and `version` CLI
  commands for schema-v2 cassettes.

### Changed

- **Breaking:** removed the CLI's offline math `record` and `replay`
  commands. The math example remains under `examples/`.
- **Breaking:** schema-v1 cassettes are rejected by the new session API;
  re-record under schema v2. See `docs/migration.md`.

### Fixed

- Repeated identical requests now consume responses by occurrence.
- Matching preserves nested meaningful fields unless explicit JSON-pointer
  paths are ignored.
- Schema-v2 validation checks typed outcomes, digest, keys, counts,
  occurrences, status, and built-in privacy patterns.
- Schema-v2 diffs detect request and intermediate response changes.
- Scrub and mode-all replacement refuse unrelated directories.
- Tool arguments are snapshotted before execution; failed calls are recorded.
- Session requests and outcomes are redacted before cassette writes.

This is development work on `v1-production`; v1.0.0rc1 has not been released.
