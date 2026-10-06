# ADR-0003: Use Content-Addressed Request Hashes for Replay Lookup

Status: Superseded by ADR 0011

Request hashes remain the identity; per-key occurrence queues replace the old single-response lookup.

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Context:
  - Replay must find the cached response for the exact meaningful request.
  - Raw request payloads may contain unstable metadata.
- Decision:
  - Normalize request data and compute SHA-256 hashes for cassette lookup.
- Consequences:
  - Replay lookup can be deterministic.
  - Request normalization must be conservative and well-tested.
  - Meaningful request changes should produce different hashes.
