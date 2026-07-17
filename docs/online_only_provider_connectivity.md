# Online-only provider connectivity (Phase 7C)

## Scientific purpose

Phase 7C audits whether an external provider can answer a limited organism query. It records URL, query, organism, time, status, record count and a bounded error. Connectivity is not biological evidence.

## Status interpretation

- `success`: the provider returned one or more recognizable records.
- `no_results`: this query returned no records; it does not demonstrate biological absence.
- `unresolved`, `timeout`, `http_error`, `schema_error`, `unavailable` or `provider_failed`: the provider could not be interpreted and no negative claim is allowed.
- `skipped` or `not_configured`: no query was attempted.

All external providers are secondary (`blocking=false`). UniProt remains seed/annotation metadata and is not experimental evidence.

## Run

```powershell
python scripts/run_online_only_multiorganism_batch.py --organism-keys escherichia_coli --run-label example --check-provider-connectivity
```

Outputs are written to `results/online_only_provider_connectivity/<run_id>/`. Online availability, API changes and rate limits constrain the audit.
