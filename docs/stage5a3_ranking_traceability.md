# Stage 5A.3 — Ranking traceability and score semantics audit

Stage 5A.3 is a read-only audit stage applied to an already-completed Stage 5A.2 run. It was introduced after the H. pylori 26695 benchmark showed that the Stage 5A.2 audit field named `final_score` could refer to a reported score column such as `nodo_score`, while the final Phase 3 ranking itself is ordered primarily by `meta_priority_score_v3` and then by additional tie-break fields.

Stage 5A.3 does not change candidate discovery, provider evidence, Functional Node Theory, therapeutic ranking weights, DIAMOND settings, or candidate order.

## Purpose

The stage makes four ranking concepts explicit and separate:

1. candidate seed rank;
2. Functional Node Theory score and rank;
3. Phase 3 therapeutic priority score and rank fields;
4. final row order in `ranking_nodos.csv`.

It also preserves the Stage 5A.2 `final_score` value as a legacy reported score so prior runs remain auditable without silently changing their meaning.

## Inputs

Stage 5A.3 requires an existing Stage 5A.2 run containing:

```text
<run_dir>/workspace/results/stage5a2_candidate_seed_audit.csv
<run_dir>/workspace/results/ranking_nodos.csv
<run_dir>/workspace/data_processed/phase3_features.csv
```

If available, it also reads:

```text
<run_dir>/workspace/results/stage5a2_manifest.json
```

No provider is contacted and no scoring function is called.

## Ranking semantics

The current NODOX reporting path sorts Phase 3 candidates using the available columns in this order:

```text
included_in_therapeutic_ranking
meta_priority_score_v3
evidence_quality_score
functional_node_theory_score
confidence_ceiling
meta_priority_score_v2
```

Stage 5A.3 therefore treats `meta_priority_score_v3` as the primary therapeutic score when that column exists. If it does not exist, it falls back through the explicit score-priority list recorded in the implementation.

The final rank reported by Stage 5A.3 is always defined as:

```text
1-based row order in ranking_nodos.csv
```

This avoids silently conflating a score column with the ordering semantics of the final report.

## Output fields

The benchmark trace includes:

- canonical benchmark token;
- exact accession/gene identity used for matching;
- Stage 5A.2 legacy final rank and reported score;
- explicit final rank and its definition;
- primary therapeutic score and score-column name;
- complete ranking sort-column list and the benchmark's values for those columns;
- Functional Node Theory score, rank, confidence and label;
- evidence-quality and confidence-ceiling values;
- Phase 3 v2/v3 scores and Phase 3 rank columns when present;
- evolutionary escape, redundancy and host-similarity fields when present;
- seed-to-FNT, FNT-to-final and seed-to-final rank deltas;
- whether the legacy Stage 5A.2 score column has the same semantics as the primary therapeutic score.

## Outputs

```text
<run_dir>/workspace/results/stage5a3_rank_trace.csv
<run_dir>/workspace/results/stage5a3_manifest.json
```

When a review package exists, both files are copied into:

```text
<run_dir>/review_package/
```

The manifest records SHA-256 hashes of the source CSVs and states explicitly that providers were not rerun, scoring was not recomputed, ranking order was not changed, and Functional Node Theory weights were not changed.

## H. pylori 26695 command

After Stage 5A.2 has completed, run:

```bash
python scripts/run_stage5a3_rank_trace.py \
  --run-dir results/20260812_hpylori_26695_stage5a2_blind
```

This reuses the completed Stage 5A.2 results. It does not require UniProt, STRING, InterPro, VFDB, DEG, BV-BRC, Europe PMC, or DIAMOND connectivity.

## Interpretation

For the H. pylori benchmark, Stage 5A.3 is intended to answer questions such as:

- Did PBP1A rise because of Functional Node Theory or because of a downstream therapeutic score?
- Does GyrA fall because of the evolutionary-escape penalty, evidence quality, or a later tie-break rule?
- Is a value previously labelled `final_score` actually the score that determined final rank?
- How much did each benchmark move from seed rank to FNT rank and from FNT rank to final therapeutic rank?

These are audit questions. Stage 5A.3 must not be used to tune a benchmark target upward or downward.

## Non-goals

Stage 5A.3 does not:

- change Functional Node Theory weights;
- change therapeutic ranking weights;
- recompute any score;
- rerun provider orchestration;
- resolve missing biological evidence;
- alter DIAMOND or host-similarity thresholds;
- change candidate discovery or benchmark identity;
- reorder `ranking_nodos.csv`.

Any later recalibration should be performed only after Stage 5A.3 establishes which evidence and score component is responsible for the observed benchmark rank.
