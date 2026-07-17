# Online-only multi-organism validation

## Scientific purpose

Online-only mode creates an isolated computational validation workspace from bounded external
provider queries. It does not import `user_curated` inputs, packaged demo data, or curated
snapshots as hidden defaults. Its outputs are hypotheses for review, not experimental evidence.

The flow is no longer limited to *Pseudomonas aeruginosa*. Organism identity, output slug,
taxonomy id and optional strain are parameters recorded in `online_only_run_manifest.json` and
the review report.

## Configured organisms

`config/online_only_organisms.json` currently defines:

- `pseudomonas_aeruginosa` (taxon 287)
- `escherichia_coli` (taxon 562)
- `mycobacterium_tuberculosis` (taxon 1773)
- `mycobacterium_tuberculosis_h37rv` (strain H37Rv, taxon 83332)

These entries are explicit configuration, not evidence snapshots. Adding a supported organism
requires a new registry entry, not a source-code edit.

## Run by configuration key

```powershell
python scripts/run_online_only_validation.py --organism-key pseudomonas_aeruginosa
python scripts/run_online_only_validation.py --organism-key escherichia_coli
python scripts/run_online_only_validation.py --organism-key mycobacterium_tuberculosis
python scripts/run_online_only_validation.py --organism-key mycobacterium_tuberculosis_h37rv
```

## Run with manual parameters

```powershell
python scripts/run_online_only_validation.py --organism "Escherichia coli" --organism-slug escherichia_coli --taxon-id 562
python scripts/run_online_only_validation.py --organism "Mycobacterium tuberculosis" --organism-slug mycobacterium_tuberculosis --taxon-id 83332 --strain H37Rv --strain-slug h37rv
```

Explicit manual parameters override values loaded through `--organism-key`. Use `--run-dir` for a
specific isolated directory and `--max-candidates` to bound candidate discovery. STRING,
InterPro or literature metadata can be disabled with `--disable-string`, `--disable-interpro` or
`--disable-literature`. A disabled provider is audited as `provider_disabled` and unresolved.

## Provenance and unresolved evidence

`unresolved` means that a layer did not provide usable matched evidence. It can reflect a missing
taxon id, provider failure, empty response, unavailable implementation or an explicitly disabled
provider. It is not success, negative biological evidence, or a silent failure.

Online inputs remain under `data_external/`. The run sets `allow_demo_data=False` and does not
create or consume `data_user/` evidence. Curated snapshots, user-curated datasets and packaged
demo data retain their separate provenance categories.

## Scoring and interpretation

This phase does not modify scoring rules or biological interpretation.
`therapeutic_priority_score` remains the model priority, while `evidence_confidence_score`
describes evidence support and interpretability. Online retrieval is computational validation,
not wet-lab, pharmacological or clinical validation.

## Expected outputs

Runs default to `results/online_only_runs/<organism_slug>_<YYYYMMDD>/` and contain a `workspace/`
plus `review_package/`. Depending on provider and pipeline availability, expected artifacts are:

- `online_only_run_manifest.json`
- `online_only_candidate_seed_manifest.json`
- provider-specific `online_only_*_manifest.json` files
- `online_only_provider_audit.csv`
- `online_only_provenance_summary.csv`
- `online_only_candidate_interpretation.csv`
- `layer_resolution_manifest.json` and summaries
- `ranking_nodos.csv` and `ranking_nodos_phase3.csv` when the pipeline can rank candidates
- `ONLINE_ONLY_REVIEW.md`

Historical Pseudomonas runs are preserved. `scripts/run_pseudomonas_online_only_validation.py`
remains a compatibility wrapper around the generic function.

## Current limitations and next step

Provider coverage is incomplete and network availability can vary. Empty or failed retrievals
therefore remain explicit unresolved evidence. The next logical iteration is to add one stable
provider at a time behind the existing layer resolver contract, with per-provider fixtures and
confidence provenance, rather than expanding all external layers simultaneously.
