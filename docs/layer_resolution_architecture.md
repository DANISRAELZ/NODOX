# Layer Resolution Architecture

## Purpose

This phase adds a minimal resolution layer before validation so each dataset
layer can be materialized from one of four origins:

- user-supplied data
- local cache
- external source
- explicit proxy/default

The goal is to extend the existing pipeline without rewriting validation,
normalization, integration, scoring, or reporting.

## Resolution Flow

Each layer is resolved before `load_and_validate_all()` reads `data_raw/`.

The resolver checks, per layer:

1. `data_user/<layer>.csv`
2. `data_cache/<layer>.csv`
3. `data_external/<layer>.csv`
4. explicit proxy/default when allowed

The exact order depends on the configured strategy:

- `user_preferred`
- `external_preferred`
- `merge_with_priority`

The resolved table is written to `data_raw/<layer>.csv` when a concrete file is
selected or merged. If the layer falls back to proxy/default, no raw file is
materialized and the status is recorded in the layer manifest.

## Current Target Layers

- `essentiality`
- `virulence`
- `human_homologs`
- `localization`
- `host_annotation`
- `strain_conservation`
- `functional_network`
- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`

## Per-layer Metadata

After integration, each target layer exposes:

- `<layer>_source_type`
- `<layer>_source_name`
- `<layer>_is_user_supplied`
- `<layer>_is_external`
- `<layer>_is_cached`
- `<layer>_is_proxy`
- `<layer>_confidence`
- `<layer>_retrieval_status`

These columns are constant per run and provide run-level provenance directly in
`integrated_nodes.csv` and downstream outputs.

## Examples

### User priority

If these all exist:

- `data_user/essentiality.csv`
- `data_cache/essentiality.csv`
- `data_external/essentiality.csv`

and the strategy is `user_preferred`, the resolver chooses the user file.

### Cache fallback

If `data_user/virulence.csv` is missing but `data_cache/virulence.csv` exists,
the cache copy is used.

### External fallback

If neither user nor cache exists and `data_external/localization.csv` exists,
the external stub is used and copied into `data_cache/` when cache writing is
enabled.

### Proxy/default

If `clinical_impact.csv` cannot be resolved from file-based sources, the layer
is recorded as proxy/default and downstream scoring keeps using explicit proxy
logic already implemented in the project.

## Current External Support

Real providers already connected behind `fetch_layer_external_source()`:

- `essentiality` -> `deg_real`
- `virulence` -> `vfdb_real`
- `localization` -> `uniprot_real`
- `functional_network` -> `string_real`
- `human_homologs` -> `uniprot_human_gene_lookup` (partial real lookup)
- `host_annotation` -> `interpro_domain_overlap`
- `strain_conservation` -> `bvbrc_real`

Hybrid or stub-backed providers:

- `human_homologs` -> `local_reproducible_orthology` when `data_external/human_homologs_orthology.csv` is present
- `human_homologs` -> `configurable_stub` as explicit fallback when the real lookup is unavailable
- `human_homologs` -> `uniprot_human_gene_lookup+configurable_stub` when the real lookup resolves only part of the layer
- `host_annotation` -> `interpro_api+controlled_host_annotation_v1` when comparable InterPro domains are unavailable

Controlled or curated therapeutic context providers:

- `clinical_impact` -> curated organism catalog when present, otherwise `controlled_therapeutic_context_v2`
- `therapy_site_context` -> curated disease/site catalog when present, otherwise `controlled_therapeutic_context_v2`
- `curated_disease_context` -> `controlled_therapeutic_context_v2`

Legacy workspace-stub support:

`workspace_stub` remains supported by `fetch_layer_external_source()` for
backward compatibility with old configurations that materialize
`data_external/<layer>.csv`. It is no longer the default provider for the active
target layers in `config/params.yaml` or the base layer registry.

This is intentional. The architecture now supports mixing real providers and
controlled stubs layer by layer without changing the resolver contract.

## Human Homologs Provider

The `human_homologs` layer now uses a minimal real provider based on UniProt
human gene lookup.

Current behavior:

1. collect candidate bacterial proteins already present in `data_raw/`
2. use `data_external/human_homologs_orthology.csv` first when a local reproducible orthology file is available
3. otherwise query UniProt for human entries using the bacterial gene symbol
4. mark a row as real-positive only when an exact human gene-name match is found
5. keep unresolved rows as missing evidence instead of forcing `0`
6. fall back to the existing stub when the lookup is unavailable

This keeps the layer reproducible and auditable while reducing total reliance
on the old stub.

### Important limitations

- This is not a sequence homology search.
- It does not run BLAST, DIAMOND, HMMER, or orthology inference.
- It is a partial heuristic based on exact human gene-name lookup in UniProt.
- A missing UniProt hit is treated as unresolved evidence, not as proof of
  absence of a human homolog.
- Because of that limitation, this provider uses moderate confidence and can be
  combined with stub backfill when only a subset of rows is resolved.

### Retrieval statuses used for `human_homologs`

- `api_real_partial_gene_lookup`
- `api_real_partial_with_stub_backfill`
- `external_real_unavailable_fallback_stub`
- `local_orthology_file_materialized`

These statuses are propagated to the layer manifest and downstream reporting.

## Reporting Outputs

The export stage now writes:

- `results/layer_resolution_manifest.json`
- `results/layer_resolution_summary.csv`
- `results/layer_resolution_summary.md`

These outputs make the chosen source per layer explicit and reproducible.

## Future Extension

The next phases can connect real providers per layer behind the same resolver,
without changing the rest of the pipeline contract.
