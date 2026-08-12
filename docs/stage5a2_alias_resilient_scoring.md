# Stage 5A.2 — Alias-aware benchmark identity and resilient full-proteome scoring

Stage 5A.2 is a corrective extension of Stage 5A.1. It addresses two issues observed in the first strain-specific *Helicobacter pylori* 26695 run without changing Functional Node Theory weights, therapeutic ranking weights, DIAMOND thresholds, or score formulas.

## Why Stage 5A.2 is needed

Stage 5A.1 correctly restricted discovery to *H. pylori* 26695 (`taxon_id=85962`, `proteome=UP000000429`) and separated `gyrA` from `gyrB`. The resulting natural seed contained 1,554 proteins.

Two remaining problems were identified:

1. The known PBP1A benchmark is UniProt `O25319`, annotated in this proteome by ordered locus `HP_0597`, while the familiar label `pbp1A` is not present as an exact gene identifier. Exact matching therefore left the benchmark unresolved even though the protein was naturally present.
2. Full-proteome provider orchestration reached STRING and then entered the per-candidate InterPro path. In the current NODOX implementation InterPro and literature retrieval are metadata-only (`affects_score=false`), so running them over the complete proteome can delay the benchmark without changing the score.

Stage 5A.2 fixes benchmark identity and full-proteome throughput while preserving the scoring model.

## 1. Explicit exact benchmark aliases

Stage 5A.2 adds repeatable alias specifications:

```text
--benchmark-alias CANONICAL=ALIAS
--benchmark-alias CANONICAL=ALIAS1,ALIAS2
```

Aliases are compared only against exact identifiers already represented in UniProt records:

- UniProt accession;
- UniProtKB entry id;
- primary gene name;
- gene synonym;
- ordered locus name;
- ORF name.

Protein-description substrings are never used.

For PBP1A in *H. pylori* 26695:

```text
pbp1A -> O25319 -> HP_0597
```

can be represented as:

```bash
--benchmark-candidate pbp1A \
--benchmark-alias pbp1A=O25319,HP_0597
```

### Blind benchmark semantics

In `blind` mode, aliases are used only after the complete natural candidate set has already been retrieved. They label an already-discovered record for benchmark auditing. They do not change the UniProt query, perform a target-specific request, add a missing candidate, or alter candidate order.

Therefore an alias-resolved candidate can still be counted as a natural blind discovery when it was independently present in the scoped candidate universe.

## 2. Benchmark-resilient provider profile

Stage 5A.2 adds:

```text
--provider-profile benchmark_resilient
--provider-profile full
```

`benchmark_resilient` is the default. It skips only:

- InterPro host-annotation metadata;
- literature metadata retrieval.

In the current NODOX orchestration both paths are explicitly non-scoring. STRING, VFDB, DEG, BV-BRC, UniProt-derived localization, candidate seed handling, the Phase 3 pipeline, Functional Node Theory, and optional DIAMOND behavior remain under the existing orchestration.

Missing provider evidence remains unresolved. It is never converted into negative biological evidence.

`full` restores the existing provider behavior, including InterPro and literature metadata retrieval.

## Recommended H. pylori 26695 blind benchmark

```bash
python scripts/run_stage5a2_validation.py \
  --organism "Helicobacter pylori" \
  --strain "26695" \
  --taxon-id 85962 \
  --proteome-id UP000000429 \
  --max-candidates 0 \
  --benchmark-mode blind \
  --benchmark-candidate pbp1A \
  --benchmark-alias pbp1A=O25319,HP_0597 \
  --benchmark-candidate gyrA \
  --benchmark-alias gyrA=P48370 \
  --benchmark-candidate gyrB \
  --benchmark-alias gyrB=P55992 \
  --provider-profile benchmark_resilient \
  --run-dir results/20260812_hpylori_26695_stage5a2_blind
```

The accession aliases for GyrA and GyrB are not required when the exact gene names are present, but including them makes the benchmark identity contract explicit and reproducible.

## Outputs

Stage 5A.2 writes pre-pipeline artifacts before provider orchestration begins:

```text
<run_dir>/stage5a2_candidate_seed_snapshot/
<run_dir>/stage5a2_candidate_seed_audit_pre_pipeline.csv
<run_dir>/stage5a2_benchmark_identity_map.json
<run_dir>/stage5a2_preflight_manifest.json
```

If provider orchestration raises before the core runner returns, Stage 5A.2 also writes:

```text
<run_dir>/stage5a2_failure_manifest.json
```

When the pipeline reaches its normal return path, the final outputs include:

```text
<run_dir>/workspace/results/stage5a2_candidate_seed_audit.csv
<run_dir>/workspace/results/stage5a2_manifest.json
```

The final manifest records whether `ranking_nodos.csv` exists and sets `scoring_reached` accordingly.

## Benchmark audit fields

The Stage 5A.2 audit includes:

- canonical benchmark token;
- exact alias used, when any;
- benchmark match type;
- whether the candidate was discovered naturally;
- whether it was forced in conditional mode;
- seed rank;
- scoring selection status;
- final NODOX rank and score when available;
- Functional Node Theory rank when available;
- proteome and candidate scope;
- provider profile.

## Interpretation

| Observation | Interpretation |
|---|---|
| benchmark absent from natural scoped seed | candidate discovery/scope problem |
| benchmark natural and alias-resolved | identity/nomenclature problem corrected; not a forced discovery |
| benchmark reaches FNT but ranks low | FNT evidence/scoring requires review |
| benchmark high FNT but low final rank | downstream therapeutic/selectivity layer requires review |
| no ranking file | pipeline/provider orchestration did not reach scoring; use preflight/failure manifests |

## Non-goals

Stage 5A.2 does not tune the model to PBP1A, GyrA, or GyrB. It does not infer aliases from protein-description substrings. It does not change Functional Node Theory weights, human-homology penalties, therapeutic score weights, or experimental-validation claims.
