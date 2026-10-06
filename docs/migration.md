# Migration from the prototype API and schema v1

The prototype Python API was removed in 1.0.0rc1. Use `agentrec.session`,
Session transports, and decorated tools. The old recorder/replayer, fake math
provider, registry, normalization helpers, and CLI demo commands are no longer
shipped. Their source and tests remain in Git history at the
[last prototype commit fb5b0a9](https://github.com/vedansh-adepu/agentrec/tree/fb5b0a9d793dec61e8aff4fe85f184998e289181).

agentrec 1.x rejects schema-v1 cassettes. Re-record under schema v2; automatic
conversion would invent occurrence ordering the old per-key response files do
not contain. Keep historical cassettes for inspection with the 0.x release.
The supported optional legacy HTTPX transport is independent of the removed
prototype; it still records and replays schema-v2 cassettes.
