# Stage 5A.4.1 — Versioned DEG/VFDB scoring contract recovery

Stage 5A.4.1 follows the Stage 5A.4 H. pylori 26695 recovery run. Stage 5A.4 established that the provider files could be retrieved/versioned, but it also exposed two provider-to-scoring contract failures:

- DEG mapped 307 of 1,554 candidates, yet those positive essential-gene records did not enter the scoring layer;
- the versioned VFDB SetA snapshot was rejected because its normalized file exposed `record_id` and `description`, while the provider mapper expected explicit identifier fields such as `gene`, `protein`, or `vf_id`.

This stage repairs those contracts without changing Functional Node Theory weights, therapeutic weights, benchmark aliases, or candidate discovery.

## Scientific semantics

### DEG

DEG is integrated as **basal essentiality evidence**, not as contextual essentiality.

A positive DEG match sets:

```text
essential = 1
```

for the matched candidate in the complete frozen essentiality layer.

A candidate absent from DEG remains unresolved. Stage 5A.4.1 never converts absence from a positive essential-gene catalogue into:

```text
essential = 0
```

This matters because missing positive evidence is not evidence of non-essentiality.

DEG does **not** directly populate `contextual_essentiality_score`. The latter is a distinct Phase 3 construct based on infection-site and host-context evidence.

### VFDB

The project snapshot `data_external/vfdb.csv` is derived from VFDB SetA FASTA and stores the original identifiers inside fields such as:

```text
record_id
VFG037176(gb|WP_001081735)
```

and descriptions such as:

```text
VFG...(gb|...) (gene) description [...] [organism]
```

Stage 5A.4.1 performs a syntactic normalization that exposes only information already present in the record:

- `vf_id` from the VFG identifier;
- `protein` from the embedded sequence accession;
- `gene` from the gene token following the record identifier;
- `organism` from the terminal organism annotation;
- `function` from the original VFDB description.

No benchmark aliases are inserted. PBP1A, GyrA, or GyrB are not forced into VFDB if VFDB does not contain them.

## Two-pass recovery

The recovery intentionally uses two Phase 3 passes.

First pass:

1. reuse the exact Stage 5A.2 candidate snapshot;
2. run the existing provider orchestration with normalized VFDB and versioned DEG;
3. collect actual DEG matches and VFDB matches.

Second pass:

1. overlay positive DEG matches onto `workspace/data_external/essentiality.csv`;
2. retain the full frozen candidate universe;
3. leave unmatched candidates unresolved;
4. mark provider score-effect manifests only when actual mapped records exist;
5. rerun Phase 3 on the same candidate universe.

This design prevents candidate-set drift while allowing recovered evidence to affect scoring.

## Preflight

Use a new recovery directory:

```bash
python scripts/run_stage5a41_provider_scoring_recovery.py \
  --source-run-dir results/20260812_hpylori_26695_stage5a2_blind \
  --recovery-run-dir results/20260812_hpylori_26695_stage5a41_recovery
```

Preflight normalizes VFDB but does not contact providers or recompute scoring.

Expected outputs include:

```text
stage5a41_preflight_manifest.json
stage5a41_vfdb_normalized.csv
stage5a41_vfdb_normalized.version.txt
```

## Execute recovery

After preflight:

```bash
python scripts/run_stage5a41_provider_scoring_recovery.py \
  --source-run-dir results/20260812_hpylori_26695_stage5a2_blind \
  --recovery-run-dir results/20260812_hpylori_26695_stage5a41_recovery \
  --execute-recovery
```

The execute command requires that the recovery directory does not already contain a `workspace`. This guards against stale DEG/VFDB provider caches from a previous recovery run.

## Outputs

The final workspace contains:

```text
workspace/results/stage5a41_evidence_coverage.csv
workspace/results/stage5a41_benchmark_comparison.csv
workspace/results/stage5a41_manifest.json
```

The benchmark comparison uses the Stage 5A.3 source trace for PBP1A, GyrA, and GyrB and compares final row order, `meta_priority_score_v3`, Functional Node Theory score, and evidence quality before and after provider recovery.

## Interpretation guardrails

Stage 5A.4.1 is a provider/scoring-contract correction, not model calibration.

It does not:

- change Functional Node Theory weights;
- change therapeutic weights;
- change evolutionary escape penalties;
- alter DIAMOND thresholds;
- enable DIAMOND;
- inject benchmark candidates;
- infer non-essentiality from absence in DEG;
- infer virulence when VFDB has no exact mapped record;
- claim experimental validation.

A change in benchmark rank after Stage 5A.4.1 should therefore be interpreted as the consequence of recovered provider evidence entering the existing model, not as a benchmark-targeted adjustment.
