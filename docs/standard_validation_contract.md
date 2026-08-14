# NODOX standard validation contract

The standard validation flow is the publication-facing execution contract for retrospective and multi-organism benchmarks. It is designed to prevent a species-level or arbitrarily truncated candidate seed from being interpreted as a complete strain-level validation.

## Candidate identity

Publication benchmarks should define all of the following:

- organism name;
- strain or isolate;
- NCBI taxon identifier for the requested strain identity;
- exact UniProt `proteome_id`;
- `max_candidates=0` for the complete candidate universe.

The standard runner retrieves candidates with an exact UniProt proteome query and materializes a versioned candidate snapshot before provider enrichment. Candidate discovery is therefore separated from species-wide taxon queries.

`max_candidates=0` means **the complete exact proteome**. Positive values intentionally truncate the exact proteome and are intended for bounded smoke tests, diagnostics, or development only. They should not be reported as proteome-wide benchmark validation.

## Benchmark registry

Exact strain profiles are available in `config/online_only_organisms.json`:

- `escherichia_coli_k12_mg1655`
- `pseudomonas_aeruginosa_pao1`
- `helicobacter_pylori_26695`
- `mycobacterium_tuberculosis_h37rv`
- `staphylococcus_aureus_newman`

Legacy species-level keys are retained for backward compatibility, but they are not the preferred publication benchmark identities.

## DEG scoring contract

DEG is interpreted as **positive basal essentiality evidence**.

- A mapped positive DEG record sets `essential=1` for that candidate.
- A candidate absent from DEG remains unresolved.
- Absence from DEG is never converted to `essential=0`.
- DEG is not relabeled as `contextual_essentiality_score`.
- DEG is not counted twice as both basal and contextual essentiality.

After a successful positive DEG overlay, the standard flow reruns Phase 3 so the recovered evidence can affect the final ranking.

## VFDB scoring contract

The standard runner accepts already provider-compatible VFDB tables. When the configured versioned VFDB SetA snapshot exposes the historical `record_id` / `description` schema, the standard flow performs the validated Stage 5A.4.1 syntactic normalization before provider mapping.

Only actually mapped VFDB records affect virulence scoring. The normalizer extracts identifiers already present in the VFDB record and does not inject benchmark aliases.

## Reproducibility outputs

A standard run writes:

- `standard_candidate_seed_snapshot/snapshot_manifest.json` for newly retrieved exact-proteome seeds;
- `workspace/results/standard_validation_manifest.json`;
- `workspace/results/standard_provider_scoring_contract_manifest.json`;
- the normal provider audit and review package;
- the final `workspace/results/ranking_nodos.csv`.

The standard manifest records the requested identity, proteome, candidate scope, effective candidate count, provider contracts, and whether provider recovery required a second Phase 3 scoring pass.

## Model invariants

This architecture change does **not** recalibrate NODOX.

- Functional Node Theory weights are unchanged.
- Therapeutic weights are unchanged.
- No benchmark target is injected into the candidate universe.
- Missing provider evidence remains missing/unresolved rather than being treated as negative biological evidence.

## Example

A complete strain-level benchmark can be launched through the standard CLI with a configured profile:

```bash
python scripts/run_online_only_validation.py \
  --organism-key helicobacter_pylori_26695 \
  --max-candidates 0 \
  --online-source-mode online_strict
```

A positive `--max-candidates` value is an explicit bounded run, for example:

```bash
python scripts/run_online_only_validation.py \
  --organism-key helicobacter_pylori_26695 \
  --max-candidates 25
```

The latter is useful for pipeline diagnostics but is not equivalent to a complete proteome validation.
