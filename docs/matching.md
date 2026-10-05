# Matching

The default version-1 policy hashes its own name/version/config plus the request.
HTTP inputs are uppercased method, lowercased scheme/host, explicit or default port,
path (empty becomes `/`), sorted decoded query pairs with blank values retained,
selected headers (none by default), and the body. JSON content-types parse into
canonical values; other or invalid JSON bodies use a raw-byte SHA-256. Fragments
and URL credentials are not match inputs. Query duplicate ordering is normalized.

Canonical encoding sorts dictionary keys and preserves list order, Unicode,
booleans, nulls, integers, and floats. `1` and `1.0` differ. Non-finite floats have
explicit tags. Unknown objects and non-string keys fail instead of being coerced.
SHA-256 collisions are theoretically possible; this is not a semantic-equivalence
solver. Numeric spellings parsed to the same Python value can normalize equally.

Ignore fields only through explicit `ignore_body_paths` JSON pointers or
`ignore_query` names. Pointers support `~0`, `~1`, dictionary keys, and array
indices. Array deletion shifts later positions; multiple pointers apply in the
configured order. Tool keys use tool name and all canonical arguments; HTTP ignore
paths do not strip tool arguments. `match_headers` opts in header names.

The stored policy identity/config must match on replay unless
`allow_policy_mismatch=True`. That escape hatch permits opening; it does not
magically make incompatible keys match. Bodies containing secrets change keys
unless ignored. Redacted key inputs cannot be fully reverified from disk.
