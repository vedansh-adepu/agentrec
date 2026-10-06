# API stability

Package releases follow SemVer after 1.0.0; release candidates may change before
the final release. The supported Python API is exactly `agentrec.__all__` plus
the documented Session methods/properties and configuration class methods.
Other modules are implementation details and their direct imports are unsupported.
Legacy v0 code lives under `_legacy` for historical tests; its former import
paths are removed and it is not a supported 1.x API.

Public names: AgentRecError, MatchPolicy, RecordMode, Redactor, ReplayExhaustedError,
ReplayMissError, ReplayOrderError, ReplayedToolError, ReplayedTransportError, Session,
UnplayedInteractionsError, __version__, legacy_async_httpx_transport,
legacy_httpx_transport, session.

Deprecations will warn for at least one minor release before removal in the next
major release. Error codes are stable within 1.x. Tests freeze the exported names.
The cassette schema version is independent of the package version; unsupported
schemas fail clearly. v1 is rejected rather than automatically converted.
