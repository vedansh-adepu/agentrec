# Performance

These are real local measurements, not CI-runner measurements or provider latency.
Command: `python benchmarks/run.py` (default sizes 100/1,000/10,000, three repeats).
Platform: macOS 26.6.2, ARM64; Python 3.13.2. The sandbox did not expose the CPU
model, so only the verified architecture is reported. Each timing is the median
of three runs. All upstream responses come from httpx2.MockTransport; no sockets
or external services are used. The script prints JSON and uses temporary cassettes.

| Interactions | Pass-through µs/request | Record µs/request | Record overhead µs/request | Replay µs/request | Load + index ms | Session open ms | Loader/index peak MiB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 36.093 | 197.28 | 161.187 | 70.753 | 0.888 | 2.843 | 0.455 |
| 1000 | 34.785 | 200.021 | 165.236 | 87.962 | 7.297 | 28.133 | 4.527 |
| 10000 | 38.869 | 230.673 | 191.804 | 75.469 | 103.355 | 282.388 | 45.38 |

## Interpretation

At 10,000 interactions, replay is 0.075469 ms/request, below the 1 ms target;
load plus index is 0.103355 s, below the 1 s target locally. Full session opening
includes integrity validation and is separately reported. The CI-runner target
has not been measured; run the same script there before claiming it is met.

Record timing includes request normalization, redaction, validation, and in-memory
buffering, but excludes atomic finalize/fsync. Pass-through includes HTTP client
and mock transport overhead. Replay timing includes the client, key computation,
queue lookup, and response construction; session loading is excluded.

Memory is tracemalloc peak for a fresh load/index, not process RSS or recording
peak. Models retained by other benchmark stages are released before tracing.
The workload repeats one small JSON request and a fixed response to exercise
occurrence queues. It does not model large SSE streams, diverse keys, privacy
regex worst cases, misses, or concurrent agents. Miss diagnostics scan recorded
interactions; successful key lookup is indexed. Bodies and interactions are
buffered in memory, so large runs can consume considerably more memory.

The smoke test validates actual offline record/replay and measurement fields,
without asserting timing thresholds that would be flaky on shared hardware.
