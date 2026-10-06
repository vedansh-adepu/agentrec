# ADR-0007: Use Safe AST Parsing for Calculator Instead of `eval`

Status: Retired with the prototype calculator

The prototype calculator is no longer part of the supported v1 API; see [migration](../migration.md).

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Context:
  - The built-in calculator should support simple arithmetic.
  - Direct `eval` would be unsafe and unnecessary.
- Decision:
  - Parse expressions with `ast`.
  - Allow only numeric constants, `+`, `-`, `*`, `/`, parentheses, and unary signs.
- Consequences:
  - Calculator behavior is safe and deterministic.
  - Unsafe expressions are rejected with clear errors.
