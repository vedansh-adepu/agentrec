# ADR-0002: Start With Fake/Offline Provider Before Live OpenAI/Anthropic Providers

Historical 0.x decision; review the 1.x ADRs (0011–0016) for current guarantees.


- Status: Accepted
- Context:
  - Live providers introduce network, credentials, rate limits, cost, and nondeterminism.
  - The MVP must prove deterministic record/replay behavior first.
- Decision:
  - Start with a deterministic fake provider.
  - Do not add live OpenAI or Anthropic providers until the offline MVP is correct.
- Consequences:
  - Tests can run without secrets or network access.
  - Provider abstractions can be shaped by local behavior before live integrations.
