# Unresolved Virulence Layer

## Purpose

Online-only multi-organism runs can proceed even when a real virulence provider is not implemented, fails, or returns no usable records. The pipeline now materializes a conservative `virulence` layer marked as unresolved so downstream integration can keep the same table contract.

## Generated Files

When either file is missing, the helper can create:

- `data_processed/validated_virulence.csv`
- `data_processed/normalized_virulence.csv`

Existing virulence files are not overwritten when both are already present.

## Values

Every generated row is explicitly unresolved:

- `virulence_factor`: empty
- `virulence_score`: missing
- `evidence`: `unresolved`
- `source_database`: `provider_not_implemented`
- `mapping_confidence`: `0.0`
- `retrieval_status`: `unresolved`

No gene is marked as a positive virulence factor.

## Identifier Sources

Protein identifiers are collected from existing workspace tables in this order:

1. `data_processed/normalized_localization.csv`
2. `data_processed/validated_localization.csv`
3. `data_processed/normalized_essentiality.csv`
4. `data_processed/validated_essentiality.csv`
5. `data_processed/normalized_uniprot_annotations.csv`
6. `data_raw/uniprot_annotations.csv`
7. `data_external/localization.csv`
8. `data_external/essentiality.csv`

Accepted identifier columns are `protein_id`, `protein_id_canonical`, `protein_id_original`, `uniprot_accession` and `accession`.

## Limitations

This fallback preserves pipeline continuity only. It is not evidence of absence of virulence and must not be interpreted as negative biological evidence.
