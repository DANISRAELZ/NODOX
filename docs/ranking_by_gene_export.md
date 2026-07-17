# Ranking By Gene Export

## Purpose

`results/ranking_nodos_by_gene.csv` is now generated automatically from `results/ranking_nodos.csv` during result export. It provides a compact one-row-per-gene view while preserving the full protein/accession-level ranking unchanged.

## Collapse Rule

The exporter selects the first available gene-like column from:

`gene`, `gene_name`, `gene_symbol`, `preferred_gene_name`, `locus_tag`, `target_gene`, `node_name`, `protein_name`, `protein_id`.

The value is stripped, empty values become `unknown`, and multi-value labels separated by `;`, `,` or `|` use the first segment.

## Score Rule

Rows are ordered by the first available score column from:

`meta_priority_score`, `therapeutic_priority_score`, `priority_score`, `score`.

For each `gene_collapse_key`, the row with the highest score is retained.

## Output Columns

The exported table preserves the ranking columns already present, including organism metadata when available, and adds:

- `gene_collapse_key`
- `accessions_collapsed`

## Limitations

This file is a reporting convenience only. It does not change scores, weights, therapeutic roles, or the original `ranking_nodos.csv`.
