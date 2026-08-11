# Stage 5A — High-recall candidate discovery and benchmark audit

Stage 5A separates **candidate discovery** from the existing NODOX scoring model. It is designed to answer two different validation questions without changing Functional Node Theory weights or the final scoring formula.

1. **Blind benchmark:** can NODOX discover a known pharmacological target without being told to include it?
2. **Conditional benchmark:** if an expected target is explicitly injected into the candidate set, does the existing downstream model rank it appropriately?

A conditional target is always marked as forced and **must not be counted as a blind discovery success**.

## What changes

Stage 5A adds a dedicated runner:

```text
scripts/run_stage5a_validation.py
```

and a candidate-discovery module:

```text
src/nodos_funcionales/stage5a_candidate_discovery.py
```

The normal `run_online_only_validation.py` behavior remains unchanged. Its historical bounded seed remains available for fast provider diagnostics.

Stage 5A retrieves UniProt candidates with cursor pagination. A page size of 500 is used by default. `--max-candidates 0` means retrieve the complete UniProt result set for the requested taxon before downstream NODOX processing.

## Blind H. pylori benchmark

```bash
python scripts/run_stage5a_validation.py \
  --organism "Helicobacter pylori" \
  --taxon-id 210 \
  --max-candidates 0 \
  --benchmark-mode blind \
  --benchmark-candidate pbp1A \
  --benchmark-candidate gyrA \
  --benchmark-candidate gyrB
```

For benchmark identifiers, UniProt accessions are preferred when known because they are less ambiguous than gene or protein aliases.

The blind run never performs target-specific retrieval to add a missing expected target. If a benchmark target is absent, the audit records that absence instead of silently inserting it.

## Conditional diagnostic benchmark

```bash
python scripts/run_stage5a_validation.py \
  --organism "Helicobacter pylori" \
  --taxon-id 210 \
  --max-candidates 500 \
  --benchmark-mode conditional \
  --benchmark-candidate pbp1A \
  --benchmark-candidate gyrA \
  --benchmark-candidate gyrB
```

In conditional mode, a benchmark target not present in the natural bounded seed may be resolved with a target-specific UniProt query and inserted explicitly. If insertion would exceed a positive candidate limit, a non-benchmark candidate from the tail is displaced and the audit records the displacement.

## Outputs

Each Stage 5A run writes:

```text
<run_dir>/stage5a_candidate_seed_snapshot/
    snapshot_manifest.json
    uniprot_seed_records.json
    candidate_seed.csv
    candidate_proteins.faa

<run_dir>/stage5a_candidate_seed_audit_pre_pipeline.csv

<run_dir>/workspace/results/
    stage5a_candidate_seed_audit.csv
    stage5a_manifest.json
```

The final audit records, when available:

- UniProt accession
- gene
- benchmark token
- whether the target was requested by the benchmark
- whether it was discovered naturally
- whether it was forced in conditional mode
- seed source
- natural seed rank
- selected seed rank
- whether it reached scoring
- exclusion reason
- whether a sequence was available
- final NODOX rank
- final score and score-column name
- Functional Node Theory rank when `functional_node_theory_score` is present

## Interpretation contract

Stage 5A deliberately does **not** change:

- Functional Node Theory weights
- human-homology penalties
- therapeutic ranking weights
- provider evidence semantics

This makes it possible to distinguish a candidate-discovery failure from a scoring failure.

| Blind result | Conditional result | Interpretation |
|---|---|---|
| Missing | High rank | Candidate-discovery problem |
| Present, low rank | Low rank | Scoring/evidence problem |
| Missing | Low rank | Both discovery and downstream ranking require review |
| Present, high rank | High rank | Expected behavior |

## Important limitation

High-recall discovery does not automatically remove provider-specific downstream caps. A provider may still process only a bounded number of candidate genes. Stage 5A therefore proves that a candidate entered the NODOX pipeline and records its ranking status, but complete full-proteome enrichment across every external provider is a separate scaling problem.

Stage 5A outputs remain computational hypotheses and do not constitute pharmacological, clinical, or wet-lab validation.
