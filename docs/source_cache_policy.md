# Source Cache Policy

## Current online source

This version supports one online source:

- STRING

## Cache location

The STRING cache is stored per workspace in:

- `<workspace>/config/string_network_cache.json`

This keeps the cache tied to:

- the organism context
- the queried protein set
- the local workspace state

## Cache contents

Each cache entry stores:

- cache key
- timestamp
- source/provider
- organism name
- taxon id
- transformed `functional_network` rows
- manifest metadata

This makes the cache reusable offline and auditable later.

## Cache behavior

- `offline_only`: uses cache only
- `cache_first`: uses cache first and queries the provider only if needed
- `online_optional`: tries the provider but falls back to cache when possible
- `--refresh-online-cache`: bypasses the matching cached entry
- `--no-write-online-cache`: avoids mutating cache during the run

## Limitations

The current policy supports refresh at query level, not selective invalidation of
single proteins or edges. That is left documented as a next step rather than
implemented prematurely.
