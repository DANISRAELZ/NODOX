# STRING Mapping Audit Protocol

## Purpose

STRING enrichment can change functional-network features and downstream
therapeutic prioritization. That effect is only interpretable if each STRING
mapping remains traceable from the local project identifiers to the identifiers
returned by STRING.

This protocol defines how to audit the relationship between:

- local `protein_id`
- local `gene`
- local `locus_tag`, when available
- STRING `stringId`
- STRING `preferredName`
- STRING `ncbiTaxonId`
- the final `protein_id` and `gene` used by the pipeline

The goal is not to block online use. The goal is to prevent ambiguous mappings
from being mistaken for strong curated evidence.

## Scientific Risk

STRING may return a valid `stringId` while the `preferredName` differs from the
local gene symbol. This can happen because of locus tags, synonyms, strain-level
annotation differences, or API mapping ambiguity. If the pipeline treats that
mapping as fully resolved, network-derived scores can look more certain than
the identifier evidence supports.

The main risk is over-interpreting an online functional-network signal as direct
support for a specific therapeutic node when the mapping is ambiguous.

## Mapping Audit Output

When STRING is fetched or served from cache, the workspace should contain local
audit outputs:

```text
results/string_mapping_audit.csv
results/string_mapping_audit.md
```

These files are generated evidence for the current workspace. They must not be
versioned as curated evidence.

The CSV uses these conceptual fields:

- `input_protein_id`
- `input_gene`
- `input_locus_tag`
- `query_sent_to_string`
- `string_id_returned`
- `preferred_name_returned`
- `ncbi_taxon_id`
- `mapping_status`
- `mapping_confidence`
- `mapping_warning`
- `used_as_final_protein_id`
- `used_as_final_gene`
- `evidence_source`
- `run_kind`
- `cache_status`

## Mapping Status Definitions

`exact_match`

High-confidence mapping. The returned STRING preferred name or STRING id suffix
matches the local gene or another accepted local identifier.

`synonym_match`

Medium-confidence mapping. The local gene is not the returned preferred name,
but appears in STRING annotation or another documented synonym-like field.

`locus_tag_match`

Medium/high-confidence mapping. The returned STRING preferred name or id suffix
matches the local `locus_tag` rather than the local gene symbol.

`preferred_name_mismatch`

The STRING id can be reconciled with the local protein id, but the returned
`preferredName` differs from the local gene. This does not invalidate the run,
but it must remain auditable and should not be promoted to curated evidence
without review.

`taxon_mismatch`

The returned STRING taxon differs from the expected organism taxon. This is a
strong warning condition. The record should not increase confidence in a
therapeutic interpretation without manual resolution.

`ambiguous_mapping`

STRING returned multiple candidates for the same query or the returned
identifier cannot be reconciled with local `protein_id`, `gene`, or `locus_tag`.
This should be treated as low-confidence online evidence.

`missing_mapping`

No STRING mapping was returned for the local candidate. This is absence of a
mapping, not evidence that the protein lacks functional interactions.

`fallback_mapping`

The evidence was not retrieved from a fresh successful API response and should
be interpreted through the fallback/cache provenance fields.

`unresolved`

Internal default for records that cannot be classified. These require review
before curation.

## Confidence Rules

- `exact_match`: high confidence for identifier mapping.
- `locus_tag_match`: moderate/high confidence, because locus tags can be the
  stable bacterial identifier even when gene symbols vary.
- `synonym_match`: medium confidence, because it depends on annotation text.
- `preferred_name_mismatch`: degraded confidence; keep the network usable but
  flag the record.
- `taxon_mismatch`: confidence should be degraded to zero for mapping evidence.
- `ambiguous_mapping`: low confidence; do not let it become curated evidence
  without manual review.
- `missing_mapping`: record as absence of mapping, not negative biological
  evidence.
- `fallback_mapping`: separate from fresh API evidence and cache reuse.

These rules do not change prioritization weights by themselves. They add
traceability so future scoring changes can decide how to treat mapping quality.

## Interpreting STRING Fields

`stringId`

STRING's internal protein identifier. It often includes a species/taxon prefix
and a protein or locus-like suffix. It should be retained as provenance, not
silently substituted for local `protein_id`.

`preferredName`

STRING's preferred label for the mapped protein. It can differ from the local
gene. A different `preferredName` is a warning, not automatic proof that the
mapping is wrong.

`ncbiTaxonId`

The taxon returned by STRING. If present and different from the expected taxon,
the mapping should be treated as a taxon mismatch.

Interaction partners

STRING edges are used to derive network centrality, bottleneck, redundancy and
dependency proxies. Those derived values inherit the mapping status of the local
proteins involved.

## Evidence Separation

STRING outputs must keep these evidence states separate:

- fresh online API evidence
- cache reuse
- fallback after API failure
- curated evidence
- local demo/template evidence
- stub or proxy evidence
- missing data
- absence of evidence
- real negative evidence

Fresh online data and cache data can support exploratory audit, but they are not
curated snapshots until reviewed.

## Snapshot Curation Gate

A STRING-derived result must not become a curated snapshot if any of these are
true:

- unresolved `taxon_mismatch` records exist
- high-impact Top 10 candidates depend on `ambiguous_mapping`
- high-impact Top 10 candidates depend on unresolved `preferred_name_mismatch`
- the run used fallback but is described as fresh evidence
- cache provenance is missing or cannot be reproduced
- organism, strain or taxon metadata are incomplete
- mapping review status is not documented

## Curated Snapshot Structure

Future curated snapshots should use a structure like:

```text
data_curated/
  organisms/
    pseudomonas_aeruginosa_pao1/
      README.md
      functional_network_curated.csv
      string_mapping_review.csv
      curation_manifest.json
    corynebacterium_pseudotuberculosis/
      README.md
      functional_network_curated.csv
      string_mapping_review.csv
      curation_manifest.json
```

Do not populate these files automatically from online runs.

The curation manifest should include:

- `organism`
- `strain`
- `taxonomy_id`
- `source_database`
- `source_version_or_access_date`
- `curator`
- `curation_date`
- `input_files`
- `evidence_types`
- `mapping_review_status`
- `accepted_records_count`
- `rejected_records_count`
- `ambiguous_records_count`
- `notes`
- `intended_use`
- `not_intended_for`
- `reproducibility_notes`

## Minimum Criteria for Multiorganism Snapshots

Before accepting a curated multiorganism STRING snapshot:

- every accepted row must have reviewed mapping status
- ambiguous and rejected mappings must remain in `string_mapping_review.csv`
- taxon ids must match the organism/strain intent
- fresh/cache/fallback provenance must be explicit
- source access date or version must be recorded
- the snapshot must be reproducible from documented inputs
- demo data must not be relabeled as real evidence
