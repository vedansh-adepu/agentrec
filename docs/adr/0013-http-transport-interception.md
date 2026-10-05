# ADR 0013: HTTP transport interception

## Context

SDK-specific wrappers would need separate integration logic for every model
provider and would miss retries performed below the application layer.

## Decision

The v1 session supplies sync and async httpx2 transports to official SDK
clients. Both model requests and SDK retries pass through the same occurrence
index. The legacy httpx adapter is deferred to its optional-extra phase.

## Consequences

Applications pass an HTTP client when constructing the SDK. Transport
exceptions and SSE responses are visible at the HTTP boundary. The harness
does not intercept network activity that bypasses the supplied transport.
