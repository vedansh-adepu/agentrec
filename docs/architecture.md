# Architecture

A Session chooses the mode, loads/validates an existing cassette, owns the
matching/redaction policies, and maintains the interaction buffer and replay index.
HTTP transports intercept SDK requests at the provided HTTP client boundary.
The tool decorator snapshots arguments before execution and records results/errors.

Illustrative architecture diagram:

```text
agent code -> SDK client -> supplied sync/async transport
           -> rec.tool   -> decorated sync/async function
                              |
                           Session
                     key + mode + replay index
                        /              \
                recorded outcome    upstream/tool body
                        \              /
                     redacted interaction buffer
                              |
                 atomic interactions.jsonl then cassette.json
```

A matching replay request consumes its next per-key occurrence. Mode none never
falls through to upstream or the decorated tool body; once also seals existing
cassettes. New episodes records misses and all replaces owned recordings.
An SDK may catch and wrap an agentrec error; its cause retains the replay error.

Recording seq reflects completion order. A session lock protects queue/buffer
accounting across threads/tasks, but callers must finish their tasks and consume
streams before closing the session. Streaming forwards chunks progressively and
buffers decoded bytes. Early close drains the remainder before recording; a
midstream transport error records an error outcome. Finish/drain streams before
closing the session. Replay preserves the outcome/body, not original chunk timing.
Strict global order is inappropriate for nondeterministic concurrent agents.

Finalize writes interactions then metadata with a digest, fsync, and atomic file
replacement. This detects interrupted two-file replacement but is not a transaction
across both files. Recording sessions hold the writer lock from opening through close; the lock is
advisory and a crash can leave a stale lock;
inspect its PID before removing it. The recorder is not a process sandbox.

See the [ADRs](adr/0011-per-key-occurrence-queues.md) for the core trade-offs.

Validation binds the digest to the exact bytes used to parse replay interactions,
so it cannot validate a different reread while replaying the first snapshot.
Default upstream transports are created lazily only for recording, reused by the
client, and closed with it. Replay never constructs a default network transport.
