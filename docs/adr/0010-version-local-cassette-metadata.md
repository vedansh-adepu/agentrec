# ADR-0010: Version Local Cassette Metadata

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Status: Accepted
- Context:
  - Cassettes are persisted developer artifacts.
  - Replay, diff, show, and validate need a clear way to reject unsupported cassette shapes.
  - Silent acceptance of unknown cassette formats would weaken replay and validation guarantees.
- Decision:
  - Add a `schema_version` field to `RunRecord` metadata.
  - Use cassette schema version `1` for the current local filesystem format.
  - Validate the schema version before treating a cassette as structurally safe.
- Consequences:
  - New cassettes carry explicit format metadata.
  - Validation can report missing or unsupported schema versions clearly.
  - Future cassette format changes have a stable compatibility hook.
