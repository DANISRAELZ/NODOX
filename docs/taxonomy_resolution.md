# Taxonomy Resolution

## Current design

The discovery layer now supports a real optional taxonomy provider with explicit
offline-safe fallback. The current provider is the public NCBI E-utilities API.

Supported modes:

- `offline_only`
- `cache_first`
- `online_optional`
- `api_stub`
- `auto`

Legacy compatibility:

- `local` is still accepted and is normalized to `offline_only`

## Mode semantics

- `offline_only`:
  only uses local cache and local synonym mapping; never attempts network access
- `cache_first`:
  prefers cache; if there is no cached entry, resolves through the local catalog
- `online_optional`:
  tries cache first, then local normalization, then the public API; if the API
  fails or returns no usable match, it falls back honestly to the local result
- `api_stub`:
  development-only explicit stub that preserves the previous behavior
- `auto`:
  uses cache if available; otherwise it behaves like `online_optional` when the
  provider is enabled and like `offline_only` when it is disabled

## What gets recorded

The normalized taxon result keeps these fields when available:

- `organism_input_name`
- `organism_canonical_name`
- `strain_input`
- `strain_canonical`
- `taxon_id`
- `rank`
- `taxon_provider`
- `source_used`
- `resolution_mode_used`
- `cache_hit`
- `api_attempted`
- `api_success`
- `fallback_reason`
- `taxon_resolution_status`
- `taxon_resolution_notes`
- `resolution_confidence`
- `timestamp_utc`

These values are written into:

- `results/organism_profile.json`
- `results/acquisition_manifest.json`
- `results/discovery_report.md`

## Real limitation

The online path is optional and network-dependent. If the local environment has
no internet access, DNS issues, timeouts or provider-side problems, the system
does not pretend success: it records the failure and degrades to the best
available offline resolution.
