# Curated Real Evidence Phase 9A

## Purpose

Phase 9A adds a local curated evidence layer for cases where online providers are incomplete, unresolved, rate-limited, or not implemented for a specific organism. The goal is to let the pipeline evaluate Functional Node hypotheses with traceable local evidence instead of relying only on placeholders or unresolved provider states.

This phase does not fabricate evidence and does not convert missing evidence into negative evidence.

## Input Layout

Place organism-specific tables under:

```text
data_curated/organisms/<organism_key>/
```

Supported files:

```text
essentiality.csv
virulence.csv
human_homologs.csv
functional_network.csv
strain_conservation.csv
redundancy.csv
literature_support.csv
```

For Helicobacter pylori, the expected key is:

```text
data_curated/organisms/helicobacter_pylori/
```

## Common Columns

Each table should include as many of these columns as possible:

```text
gene
protein_id
evidence_status
evidence_source
source_database
reference
confidence
notes
```

Rows can match candidates by `gene`, `protein_id`, `protein_id_canonical`, `uniprot_accession`, or `locus_tag`.

## Layer-Specific Columns

Essentiality:

```text
essential
essentiality_score
```

Virulence:

```text
virulence_factor
virulence_score
```

Human homologs:

```text
human_homolog
human_similarity_score
host_similarity_penalty
selectivity_score
```

Functional network:

```text
network_centrality
pathway_bottleneck_score
functional_dependency_score
interaction_count
network_source
```

Strain conservation:

```text
strain_coverage_score
core_genome_presence
allelic_conservation
variant_burden
```

Redundancy:

```text
redundancy_penalty
low_redundancy_score
paralog_count
alternative_pathway_count
```

Literature support:

```text
literature_support_score
pmid
finding
experimental_support
```

## Configuration

Default configuration:

```yaml
curated_real_evidence:
  enabled: true
  base_dir: data_curated/organisms
  precedence:
    replace_unresolved: true
    preserve_online_real: true
  minimum_confidence: 0.5
```

If no curated tables exist, the pipeline records missing curated layers and continues unchanged.

## Evidence Semantics

- `unresolved` means the software does not yet have sufficient evidence.
- Negative evidence requires an explicit, traceable source.
- Curated fixture evidence is useful for testing integration, but it is not experimental validation.
- Curated evidence can replace provider failures, placeholders, demo-only values, or unresolved values.
- Higher-confidence online/user evidence is preserved when `preserve_online_real: true`.
- Conflicts are recorded in `curated_evidence_conflict_flags`.

## Integration With Phase 8

Curated evidence is applied before Phase 2 scoring. Therefore it can feed:

- `data_processed/phase2_features.csv`
- `data_processed/scored_nodes.csv`
- `results/ranking_nodos.csv`
- `results/ranking_functional_nodes.csv`
- `results/functional_node_theory_audit.csv`
- `results/theory_of_nodes_report.md`

The Functional Node audit exposes:

- `curated_evidence_layers`
- `curated_evidence_references`
- `curated_evidence_notes`
- `curated_evidence_missing_layers`
- `curated_evidence_conflict_flags`
- `curated_evidence_summary`

## Outputs

Phase 9A writes:

```text
results/curated_real_evidence_manifest.json
results/curated_real_evidence_summary.csv
```

These outputs document which curated files were found, which layers were missing, how many rows matched, how many cells were updated, and whether existing evidence was preserved.

## Interpretation

Curated local evidence can move a candidate from `hypothesis_only_insufficient_evidence` to a lower or moderate confidence Functional Node candidate when several independent layers support it. It must not create `high_confidence_functional_node` from low-coverage, unresolved, placeholder, demo-only, or fixture-only evidence.
