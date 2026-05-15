# Online Source Integration

## Why STRING was chosen first

This repository already had a dedicated optional layer for:

- `data_raw/functional_network.csv`

That layer feeds directly into:

- `network_centrality`
- `pathway_bottleneck_score`
- `redundancy_penalty`
- `functional_dependency_score`

It was also one of the clearest methodological weak points in the current
ranking because it was still `demo_only` in the bundled example outputs. Those
bundled outputs are controlled demonstrations, not the conceptual center of the
project and not a default organism requirement.

For that reason, STRING was a better first online source than UniProt in this
iteration: it strengthens an existing scoring layer without reopening the whole
normalization pipeline.

The integration is organism-agnostic: it uses the organism and identifiers
provided by the workspace, and any named organism in validation notes should be
read as a demo, fixture, snapshot, or controlled audit case.

## What the integration does

The integration lives in:

- `src/nodos_funcionales/string_api.py`
- `fetch_online_data.py`

It:

1. collects candidate proteins from local required tables
2. reuses the organism taxon id already handled by discovery/taxonomy
3. queries STRING optionally
4. transforms the response into a compatible `functional_network.csv`
5. writes a manifest and a report
6. caches the result locally for later offline reuse
7. can rerun the workspace pipeline and generate a real before/after impact report
8. appends a per-workspace online history entry and rebuilds a source comparison report

## What is observed and what is derived

Within the generated `functional_network.csv`:

- observed from provider:
  - STRING identifier mapping
  - network edges and confidence scores returned by STRING
- derived from provider graph:
  - `network_centrality`
  - `pathway_bottleneck_score`
  - `redundancy_penalty`
  - `functional_dependency_score`

These derived variables are useful, but they are still graph-derived summaries,
not direct biological measurements.

## Safety and fallback behavior

Supported modes:

- `offline_only`
- `cache_first`
- `online_optional`

Behavior:

- `offline_only` only uses cache and fails honestly if cache is absent
- `cache_first` prefers cache and otherwise queries STRING
- `online_optional` queries STRING but falls back to cache when possible

## Before/after audit

When `fetch_online_data.py` runs on a workspace that already has a ranking:

- it snapshots the pre-enrichment ranking
- fetches and writes the online source output
- reruns the workspace pipeline by default
- writes `results/online_enrichment_impact.csv`
- writes `results/online_enrichment_impact.md`

That audit distinguishes between:

- `ranking_changed`
- `annotation_or_provenance_only`

This matters because a provider like STRING can change network-derived scoring,
while a provider like UniProt may enrich annotation context without moving the
ranking at all.

## History and source comparison

Each online fetch now also writes:

- `results/online_source_history.jsonl`
- `results/online_source_comparison.csv`
- `results/online_source_comparison.md`

The history is append-only and records the provider, cache/API path, and the
observed impact status for that run. The comparison report then summarizes the
latest behavior of each source seen in the workspace.

This is intentionally simple: it gives a reproducible audit trail without adding
a database or a more complex state machine.

## Clean source audit

The repository now also includes:

- `audit_online_sources.py`

This command creates temporary clones of a workspace, removes the selected
source layer when it can be identified safely, reruns the pipeline to establish
a baseline, applies the source again, and measures the resulting before/after
impact.

The goal is not to prove biological truth. The goal is to estimate source-level
causal impact within the current model in a way that is:

- reversible
- offline-compatible when cache exists
- explicit about reset quality

If a source-specific layer cannot be removed safely, the audit marks that clone
as not fully clean instead of pretending the comparison is fully isolated.

## Important limitation

STRING enrichment is only as good as the identifiers provided by the workspace.
If the provider returns preferred names that disagree with the local `gene`
column, the manifest reports that explicitly. That does not automatically mean
the online call is wrong, but it does mean the enrichment should be interpreted
with caution.

## Recommended next provider

After STRING, the most natural next provider would be **UniProt** to improve
identifier context and annotation quality upstream of network enrichment.

## Optional next steps

Small follow-up steps already suggested by the current architecture:

1. add a lightweight provider interface so UniProt can be plugged in later while
   keeping STRING as default
2. support selective cache invalidation for one query entry instead of only
   full refresh by protein set
3. extend `compare_workspaces.py` to compare online provenance, cache hit/miss
   and enrichment source across workspaces
4. add guided importers for source-specific local exports such as BLAST, VFDB or
   PSORTb
5. add a before/after audit to compare how the top 10 changes when STRING
   enrichment replaces the demo network layer
6. if UniProt is added next, use it primarily to stabilize identifier context
   before a second round of STRING enrichment
