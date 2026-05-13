# Source Cache Policy

## Current online sources

This version separates two concepts:

- direct online fetch wrappers exposed by `fetch_online_source()`: STRING and UniProt;
- layer-level external providers exposed by `fetch_layer_external_source()`: STRING, UniProt localization, UniProt human homolog lookup, InterPro, DEG, VFDB, BV-BRC, curated offline catalogs, controlled providers, and traceable stubs/fallbacks.

Only `online_optional` is allowed to attempt fresh network access. Offline test runs must use cache, local files, controlled providers, stubs, or explicit missing status.

The cache policy supports the Functional Nodes Theory by preserving where each evidence layer came from and how confidently it can be interpreted. Cache reuse, snapshots and online responses are evidence logistics, not the conceptual center of the project.

## Cache location

Provider caches are stored per workspace under `config/` using filenames configured in `config/params.yaml`.

Known configured cache files:

- `<workspace>/config/string_network_cache.json`
- `<workspace>/config/uniprot_annotation_cache.json`
- `<workspace>/config/interpro_host_annotation_cache.json`
- `<workspace>/config/deg_essentiality_cache.json`
- `<workspace>/config/vfdb_virulence_cache.json`
- `<workspace>/config/bvbrc_conservation_cache.json`

This keeps the cache tied to:

- the organism context
- the queried protein set
- the local workspace state

## Cache contents

Each provider cache entry should store enough metadata to distinguish real evidence from cache reuse or fallback. For STRING and UniProt, entries store:

- cache key
- timestamp
- source/provider
- organism name
- taxon id
- transformed rows
- manifest metadata

This makes the cache reusable offline and auditable later.

## Cache behavior

- `offline_only`: uses cache only
- `cache_first`: uses cache first and queries the provider only if needed
- `online_optional`: tries the provider but falls back to cache when possible
- `--refresh-online-cache`: bypasses the matching cached entry
- `--no-write-online-cache`: avoids mutating cache during the run

The layer resolver has an additional guard: when a layer-level `data_cache/<layer>.csv` exists and the effective online source mode is `offline_only` or `cache_first`, it should not request the external provider for that layer.

If a `data_external/<layer>.csv` already exists, `fetch_layer_external_source()` may materialize it as an external file without opening network. This is a snapshot-like reuse path and must preserve `source_name`, `status`/`retrieval_status`, and `confidence`.

## Data external and curated catalogs

Layer materialization uses:

- `<workspace>/data_external/<layer>.csv`
- `<workspace>/data_external/curated_catalogs/<catalog>/<organism-or-taxon>.csv`
- repository-level `data_external/curated_catalogs/` as a fallback for curated catalogs
- repository-level `data_external/curated_snapshots/<organism-scope>/` for small versioned snapshot contracts

Curated catalogs are offline inputs. They are not fresh online evidence and should use source names such as `curated_online_*_catalog` with explicit confidence.

Curated snapshots are not volatile provider caches. They may reference cache provenance, but must not store raw fresh provider payloads unless a later protocol explicitly freezes and documents them.

## Evidence boundaries

- `api_real` and `api_real_success` indicate fresh external evidence during an allowed network mode.
- `cache` and `cache_hit` indicate reuse of prior retrieved data, not current online evidence.
- `controlled_*` providers are deterministic workspace-derived evidence, not experimental evidence.
- `configurable_stub_*` and `workspace_stub` preserve pipeline shape, but must never be interpreted as real negative or positive biological evidence.
- `missing` or `external_unavailable_*` means absence of usable data, not biological absence.

## Multiorganism design principle

Cache and snapshot policy is organism-agnostic. PAO1, `Corynebacterium pseudotuberculosis` and H37Rv are reference cases only. New organisms may have complete external evidence, user-provided evidence, partial cache, controlled offline evidence or no resolved taxon id yet.

For any organism, source status must describe what happened: queried, not queried, cache hit, cache miss, controlled, stub, fallback or missing. Lack of STRING/UniProt coverage must not be treated as negative biological evidence.

## Limitations

The current policy supports refresh at query level, not selective invalidation of single proteins or edges. Some cache helpers are still provider-specific. Consolidating common cache/provenance helpers under `src/nodos_funcionales/online/` is planned, but should be done as refactor-only commits with offline tests.
