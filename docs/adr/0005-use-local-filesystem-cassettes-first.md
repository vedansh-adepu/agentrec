# ADR-0005: Use Local Filesystem Cassettes First

Status: Superseded by ADR 0016

Local filesystem storage remains; schema v2 replaces the file layout listed below.

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Context:
  - Cassettes should be easy to inspect, diff, and test.
  - Remote storage or databases would add complexity before the MVP needs them.
- Decision:
  - Store cassettes on the local filesystem.
  - Use simple files: `metadata.json`, `trace.jsonl`, `responses/`, and `artifacts/`.
- Consequences:
  - Cassettes are transparent and easy to debug.
  - Filesystem tests can use `tmp_path`.
  - Remote storage remains a future option.
