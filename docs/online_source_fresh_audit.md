# Online Source Fresh Audit

## Purpose

This audit compares controlled online-enrichment scenarios on temporary clones
of a workspace to estimate whether a fresh API call changes:

- provenance only
- feature values
- strategic scores
- ranking
- top 10 composition

It is methodologically stronger than a cache-only replay because it can
distinguish:

- `fresh_api_run`
- `cache_reuse_run`
- `fallback_after_api_failure`
- `no_online_run`
- `mixed_run`

## Scenarios

The audit can generate:

- `baseline_no_online`
- `uniprot_only_fresh`
- `string_only_fresh`
- `combined_online_fresh`
- optional cache contrasts when `--compare-fresh-vs-cache` is enabled

Example:

```bash
python audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions/pao1_demo --sources string uniprot --compare-fresh-vs-cache
```

Guardrail:

- `--force-refresh` is compatible with fresh-only runs
- `--force-refresh` must not be combined with `--compare-fresh-vs-cache`, because cache scenarios would stop being true cache controls

## Interpretation

Important guardrails:

- a successful API call is not the same as a ranking effect
- a null fresh effect is still a valid result
- provenance-only changes should not be overstated as biological effects
- fresh-vs-cache comparisons are causal only within the current model and data

## Main outputs

- `online_source_fresh_audit.csv`
- `online_source_fresh_audit.md`
- `online_source_fresh_vs_cache.csv`
- `online_source_fresh_vs_cache.md`
- `online_source_candidate_shifts_fresh.csv`
