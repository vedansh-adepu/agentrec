# ADR-0004: Preserve Meaningful `id` Fields During Normalization

Status: Superseded by ADR 0012

The v1 policy preserves all body fields by default and requires explicit ignore paths.

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Context:
  - A generic `id` field can be meaningful in tool arguments, such as `{"id": "customer_123"}`.
  - Removing all `id` keys could make different tool requests hash to the same value.
- Decision:
  - Do not remove generic `id`.
  - Remove clearly unstable fields such as `request_id`, `trace_id`, `span_id`, `run_id`, timestamps, and random IDs.
- Consequences:
  - Tool requests with meaningful IDs stay distinguishable.
  - Future normalizer changes should avoid broad field deletion.
