# Pseudomonas aeruginosa online-only validation

> Historical compatibility example. The online-only flow is now organism-parameterized; see
> `docs/online_only_multiorganism_usage.md` for the universal runner. Pseudomonas and PAO1 data
> are not hidden defaults for other organisms.

## Purpose

This controlled run tests whether `Pseudomonas aeruginosa` candidates can be seeded and prioritized from online or external layers without injecting a full `user_curated` gene list.

The run is isolated under:

`results/online_only_runs/pseudomonas_aeruginosa_<date>/`

## Rules

- No `data_user/` inputs are required or created for the run.
- The required candidate seed is materialized as `data_external/essentiality.csv`.
- The seed uses UniProt as online candidate discovery only.
- Seeded candidates keep `essential` unresolved and `essentiality_status=unresolved_online_seed`.
- After a successful seed, the online-only runner attempts bounded downstream enrichment:
  - UniProt seed reuse for localization and basic protein metadata.
  - STRING for functional-network interaction evidence.
  - InterPro for domain metadata without inferring human homology.
  - Europe PMC metadata for bounded literature hit counts.
- Scoring logic is not changed.
- Missing online evidence remains unresolved or causes a documented graceful failure.
- VFDB, DEG, BV-BRC and evolutionary layers are reported as not implemented or unresolved unless a real matched provider result is available.

## Command

```powershell
python scripts/run_pseudomonas_online_only_validation.py --max-seed-candidates 25 --online-source-mode online_optional --taxon-resolution-mode online_optional
```

The historical command remains supported. Its wrapper delegates to the generic runner with
taxon id `287`.

If network access is blocked, the command should still generate a review package documenting the failure.

For environment-level HTTPS failures, a contract-only fallback can be run:

```powershell
python scripts/run_pseudomonas_online_only_validation.py --online-source-mode offline_only --materialize-unresolved-required-fallback
```

This fallback does not use live online access. It only checks that external-only unresolved layers can move through the pipeline without `user_curated` input.

## Outputs

The review package includes, when available:

- `ranking_nodos.csv`
- `ranking_nodos_phase3.csv`
- `layer_resolution_manifest.json`
- `layer_resolution_summary.csv`
- `online_only_provenance_summary.csv`
- provider manifests such as `online_source_manifest.json`, `vfdb_virulence_manifest.json`, and `deg_essentiality_manifest.json`
- online-only provider manifests such as `online_only_functional_network_manifest.json`, `online_only_host_annotation_manifest.json`, and `online_only_literature_support_manifest.json`
- `online_only_provider_audit.csv`
- `ONLINE_ONLY_REVIEW.md`

## Interpretation limits

`therapeutic_priority_score` ranks model priority. `evidence_confidence_score` describes support and interpretability constraints. They are separate variables.

Online candidate discovery is not experimental validation. A candidate must not be described as experimentally validated unless retrieved evidence explicitly supports that claim.

UniProt seed success is separated from essentiality evidence. In this controlled run, UniProt can provide candidates and annotations, but it does not prove a gene is essential unless an explicit retrieved essentiality field supports that claim.

STRING interactions, InterPro domains and Europe PMC records are computational or metadata evidence only. They must keep `experimental_validation_supported=false` unless an explicit parsed experimental validation workflow is added later.

## Future steps

- Add a first-class external candidate-discovery layer to the layer registry.
- Replace the temporary UniProt seed adapter with a reusable provider behind `fetch_layer_external_source()`.
- Add provider-specific confidence columns for candidate discovery, essentiality, virulence, localization and network layers.
