# Stage 4C — provider-to-contract evolutionary evidence integration

## Purpose

Stage 4C begins connecting real provider-derived biological observations to the strict evolutionary evidence contract introduced in Stage 4A and integrated into scoring in Stage 4B.

The first provider adapter is BV-BRC strain conservation. The objective is not to label every BV-BRC output as independent evolutionary evidence. The objective is to materialize one conservative, auditable canonical evolutionary variable when the existing provider layer supplies sufficient real candidate-level information.

## Why BV-BRC is the first adapter

The existing BV-BRC provider already calculates candidate-level strain-conservation information from a taxon-scoped genome query and candidate feature matches:

- `core_genome_presence`
- `strain_coverage_score`
- `allelic_conservation`
- `variant_burden`

The provider deliberately omits unmatched candidates rather than encoding absence of a match as biological zero.

These fields are useful evolutionary observations, but they are not four independent pieces of evidence.

## Correlation guard

The current BV-BRC implementation derives:

- `core_genome_presence` and `strain_coverage_score` from the same observed genome-presence fraction;
- `variant_burden` as `1 - allelic_conservation` when family information is available.

Consequently Stage 4C does **not** count these four columns as four explicit evolutionary variables or four independent evidence groups.

The first adapter materializes a single canonical variable:

```text
evolutionary_constraint_score =
    0.5 * core_genome_presence
  + 0.5 * allelic_conservation
```

`strain_coverage_score` is excluded from this canonical score because it duplicates the provider's current presence calculation. `variant_burden` is excluded because it is the inverse transformation of `allelic_conservation` in the current provider implementation.

All evidence produced by this adapter uses one independence group per taxon:

```text
bvbrc_strain_conservation_taxon_<taxon_id>
```

This design intentionally prevents correlated BV-BRC transformations from satisfying the Stage 4A independence requirement by themselves.

## Eligibility gate

The BV-BRC adapter fails closed. A row is eligible only when all of the following are true:

- the strain-conservation layer resolves from an external provider or provider cache;
- the source is identifiable as BV-BRC/BV-BRC's PATRIC lineage;
- the layer is not proxy or packaged/mixed demo data;
- the layer source type is consistent with its `is_external` or `is_cached` provenance flag;
- retrieval status is not unresolved, failed, not found, empty, or incomplete;
- candidate identity, gene, and taxon are available;
- original BV-BRC query provenance was preserved from a complete successful provider manifest;
- provider taxon agrees with the candidate taxon;
- the preserved mapping status is `exact_gene_and_taxon`;
- the original provider evidence status is `observed`;
- the original provider retrieval status was `api_real`;
- `core_genome_presence` is a real 0–1 value and not a scoring placeholder;
- `allelic_conservation` is a real 0–1 value and not a scoring placeholder.

Missing family annotation therefore remains missing evidence. It is not converted to zero allelic conservation or low evolutionary constraint.

## Mapping semantics

The current BV-BRC provider queries candidate genes within an explicit taxon scope. Eligible adapter records therefore preserve:

```text
mapping_method = bvbrc_gene_filter_with_taxon_scope
mapping_status = exact_gene_and_taxon
```

Rows lacking either gene or taxon fail closed and cannot request explicit evidence. A mismatch between the provider taxon and the candidate taxon also fails closed.

## Provider provenance transport

Stage 4C does not regenerate evidence provenance at scoring time.

During normalization, `normalization.py` reads `results/bvbrc_conservation_manifest.json`. A BV-BRC conservation row receives provider provenance only when the manifest represents a complete successful query and the row itself is identified as BV-BRC. The following fields are transported into the normalized conservation table and then through `integration.py` into `integrated_nodes.csv`:

- `conservation_source_record`
- `conservation_source_version`
- `conservation_retrieved_at`
- `conservation_mapping_method`
- `conservation_mapping_status`
- `conservation_evidence_status`
- `conservation_evidence_confidence`
- `conservation_independence_group`
- `conservation_method_scope`
- `conservation_taxon_id`
- `conservation_provider_retrieval_status`
- `conservation_provider_query_cache_key`
- `conservation_provider_source_used`

`conservation_source_record` includes the BV-BRC query cache key plus candidate and gene identity. This provides a stable query-level provenance anchor for the candidate record.

## Retrieval timestamp and cache semantics

The current BV-BRC provider manifest already preserves its original `generated_at_utc` and query cache key when a completed query is served from cache. Stage 4C therefore uses that original manifest timestamp as `conservation_retrieved_at` and ultimately as the canonical `evolutionary_constraint_score_retrieved_at`.

The scoring adapter does **not** create a new retrieval timestamp.

This means a cached reuse of the same completed BV-BRC query retains the retrieval time of the original provider evidence instead of appearing to be newly retrieved biological evidence.

Old BV-BRC caches or conservation tables that do not carry the Stage 4C provider provenance fields remain usable for historical/proxy calculations, but they fail closed for explicit evolutionary evidence. They must be refreshed or re-normalized from a valid complete BV-BRC manifest before they can be promoted through the explicit-evidence contract.

## Source version semantics

The current BV-BRC integration does not expose a formal immutable BV-BRC database release identifier. Stage 4C does not invent one.

Normalization records a reproducibility marker of the form:

```text
bvbrc_unversioned_snapshot@<original_generated_at_utc>
```

This is explicitly an unversioned provider snapshot marker, not a claim about a BV-BRC release number. A future provider-hardening stage can replace it with an official release identifier if BV-BRC exposes one without changing the Stage 4A evidence contract.

## Source type semantics

The canonical variable is passed through the unchanged Stage 4A validator.

- a live external row whose preserved provider source is `api_real` is represented as `real_external_online`;
- an externally materialized BV-BRC snapshot that is not demonstrably live in the current layer is represented as `real_external`;
- a provider-cache reuse of a previously successful real query is represented as `computed_from_real_data`.

Cache reuse does not create a new independence group and does not become a second biological source.

## Existing canonical evidence

Stage 4C does not overwrite an existing `evolutionary_constraint_score` or its existing evidence metadata.

When BV-BRC is eligible but a canonical constraint record already exists, the BV-BRC-derived score remains available as:

```text
bvbrc_evolutionary_constraint_score
```

and the audit reason is:

```text
eligible_but_existing_canonical_evidence_preserved
```

This prevents the provider adapter from silently replacing experimental, literature-curated, or user-curated canonical evidence.

## Contract behavior

A BV-BRC-derived constraint record can become one contract-valid explicit variable and one independent evidence group.

With the default Stage 4A/4B thresholds:

```text
minimum explicit variables = 3
minimum independent evidence groups = 2
```

BV-BRC alone therefore cannot enable `evolutionary_escape_supported_score`.

Example:

```text
BV-BRC evolutionary_constraint_score
  explicit variables = 1
  independent groups = 1
  supported_by_contract = false
```

If two additional valid variables come from a genuinely independent experimental or curated group, the candidate can satisfy the full contract:

```text
BV-BRC constraint                       group A
mutation tolerance experimental         group B
fitness cost experimental               group B

explicit variables = 3
independent groups = 2
supported_by_contract = true
```

The Stage 4B supported score then uses the actual BV-BRC-derived canonical value; it is not counted only for threshold purposes.

## Audit outputs

Stage 4C adds provider-adapter diagnostics:

- `bvbrc_evolutionary_evidence_eligible`
- `bvbrc_evolutionary_evidence_reason`
- `bvbrc_evolutionary_constraint_score`

Eligible materialized records also populate the existing Stage 4B canonical metadata columns for `evolutionary_constraint_score`, including source type, source database, source record, source version, original retrieval time, mapping method/status, evidence status/confidence, independence group, taxon and notes.

Common fail-closed reasons include missing original provider provenance, provider/candidate taxon mismatch, non-direct mapping, placeholder signals, demo/mixed-demo provenance, and old cache data without a reproducible query record.

## Scientific limitations

Stage 4C does not establish experimental validation of NODOX or prospective resistance prediction.

The BV-BRC constraint score is a computational transformation of real provider-derived comparative-genomic observations. It should be described as provider-derived/computed evidence from real data, not as a direct experimental measurement.

The current adapter also does not claim that strain conservation is equivalent to every dimension of evolutionary robustness. It contributes one canonical constraint variable only.

The current `source_version` is an unversioned timestamped snapshot marker because an official BV-BRC release identifier is not exposed through this integration.

STRING, DEG, VFDB, UniProt and DIAMOND are not promoted to evolutionary evidence by this patch. Each future adapter must independently justify its biological variable, mapping, provenance and independence group.
