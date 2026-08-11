# Stage 5A.1 — Strain-specific benchmark scope and strict target matching

Stage 5A.1 is a corrective extension of Stage 5A. It addresses two issues observed in the first blind *Helicobacter pylori* benchmark without changing NODOX scoring, Functional Node Theory weights, or human-homology penalties.

## Corrections

### 1. Strict benchmark identity

Stage 5A used permissive normalized substring matching. This allowed the benchmark token `gyrA` to match text derived from `DNA gyrase subunit B`, which could incorrectly mark a `gyrB` entry as satisfying both `gyrA` and `gyrB`.

Stage 5A.1 accepts benchmark matches only when the normalized token is exactly equal to one of:

- the UniProt accession;
- the UniProtKB entry identifier;
- the primary gene name;
- a UniProt gene synonym;
- an ordered locus name;
- an ORF name.

Protein-description substrings are never used for benchmark identity. Ambiguous exact matches are reported as `ambiguous_exact_benchmark_identifier` rather than resolved arbitrarily.

### 2. Strain/proteome-specific discovery

Stage 5A.1 accepts `--proteome-id`. When supplied, candidate discovery is restricted to both the requested NCBI taxon and UniProt proteome:

```text
(organism_id:<taxon>) AND (proteome:<UPID>)
```

This prevents a species-level benchmark from mixing proteins across many isolates when the pharmacological reference is a specific strain.

## H. pylori 26695 blind benchmark

For *H. pylori* strain 26695 use:

- NCBI taxon: `85962`
- UniProt proteome: `UP000000429`

Recommended command:

```bash
python scripts/run_stage5a1_validation.py \
  --organism "Helicobacter pylori" \
  --strain "26695" \
  --taxon-id 85962 \
  --proteome-id UP000000429 \
  --max-candidates 0 \
  --benchmark-mode blind \
  --benchmark-candidate pbp1A \
  --benchmark-candidate gyrA \
  --benchmark-candidate gyrB \
  --run-dir results/20260811_hpylori_26695_stage5a1_blind
```

For maximum benchmark specificity, known UniProt accessions may be supplied instead of gene symbols when available.

## Outputs

Stage 5A.1 writes:

```text
<run_dir>/stage5a1_candidate_seed_snapshot/
<run_dir>/stage5a1_candidate_seed_audit_pre_pipeline.csv
<run_dir>/workspace/results/stage5a1_candidate_seed_audit.csv
<run_dir>/workspace/results/stage5a1_manifest.json
```

The audit adds `benchmark_match_type`, `proteome_id`, and `candidate_scope`. The manifest records the exact UniProt scope query and whether the run is `proteome_strain_specific` or only `taxon_specific`.

## Interpretation

| Result | Interpretation |
|---|---|
| target absent in blind scoped seed | discovery/scope problem |
| target present but low FNT rank | Functional Node Theory/evidence issue |
| target high FNT but low final rank | downstream therapeutic/selectivity penalty issue |
| target high in both | expected recovery |

## Non-goals

Stage 5A.1 does not change Functional Node Theory weights, therapeutic ranking weights, DIAMOND thresholds, human-homology penalties, or provider evidence semantics. Provider-specific downstream caps may still limit evidence enrichment after the strain-specific candidate set has been discovered.
