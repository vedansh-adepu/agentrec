# ADR 0014: Buffered atomic finalize

## Context

Incremental writes could leave a partial cassette after an agent or transport
failure. Concurrent calls also need one sequence and occurrence order.

## Decision

A session buffers completed interactions under a lock and writes the schema-v2
files at finalize. The interaction file is replaced first and its checksummed
metadata last. A failed agent run receives failed status and an error record.

## Consequences

Recording memory grows with cassette size. Sequence reflects completion order,
so strict-order replay is unsuitable for many concurrent agents. A crash
between the two file replacements is detectable, but the two files are not one
atomic filesystem transaction.
