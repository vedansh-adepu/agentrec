# Migration from schema v1

agentrec 1.x does not replay schema-v1 cassettes. Re-record the agent run under
schema v2. The old v1 layout cannot preserve distinct occurrences of an
identical request, so automatic conversion would invent an ordering guarantee
that the data does not contain. Keep a backup of any historical v1 cassette
needed for inspection with the 0.x release.
