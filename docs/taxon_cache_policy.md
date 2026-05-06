# Taxon Cache Policy

## Cache file

The taxonomy cache is stored in:

- `config/taxon_resolution_cache.json`

It is designed to stay readable and auditable.

## Cache structure

Current structure:

- `schema_version`
- `updated_at_utc`
- `entries`

Each cache entry stores:

- `cache_key`
- `saved_at_utc`
- `refresh_count`
- `result`

The `result` field contains the normalized taxon resolution payload used by the
discovery layer.

## Behavior

- cache is reused in `offline_only`, `cache_first`, `online_optional` and `auto`
- `--refresh-taxon-cache` bypasses a matching cached entry and recomputes it
- `--no-write-taxon-cache` keeps the run reproducible without mutating cache
- legacy cache entries are migrated in-memory when read

## Scientific interpretation

A cache hit means the system reused a prior audited resolution. It does not mean
the cache entry is biologically more certain than a fresh online lookup. The
cached provenance is preserved so users can still see whether the original entry
came from local mapping, real API resolution or stub behavior.
