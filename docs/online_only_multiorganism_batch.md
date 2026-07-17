# Phase 7B: online-only multiorganism batch

## Scientific purpose

Phase 7B executes the same parameterized online-only workflow for multiple configured bacterial
organisms and consolidates provider, layer, candidate-seed and ranking audits. It is designed as
external computational validation for publication. It is not experimental, pharmacological or
clinical validation.

The batch does not change scoring rules. It records SHA-256 hashes for `scoring.py` and
`scoring_components.py` before and after execution so that this invariant is auditable.

## Command

```powershell
python scripts/run_online_only_multiorganism_batch.py --all-default-validation-organisms --run-label multiorganism_online_only_20260619 --max-candidates 25 --continue-on-error
```

For a subset:

```powershell
python scripts/run_online_only_multiorganism_batch.py --organism-keys escherichia_coli mycobacterium_tuberculosis_h37rv --run-label test_multiorganism_online_only --max-candidates 25
```

The configured keys are read from `config/online_only_organisms.json`. Pseudomonas follows the
same generic batch contract as every other organism; the historical single-organism wrapper is
not used by this runner.

## Options

- `--disable-string`, `--disable-interpro` and `--disable-literature` disable individual enrichment providers.
- `--continue-on-error` records an organism-level exception and proceeds to the next configured organism.
- `--output-dir` selects an explicit comparison directory.
- `--max-candidates` bounds UniProt candidate discovery per organism.

## Output contract

The default location is `results/online_only_multiorganism_runs/<run_label>/`. It contains:

- `batch_manifest.json`
- `batch_provider_audit.csv`
- `batch_layer_resolution_summary.csv`
- `batch_candidate_seed_summary.csv`
- `batch_ranking_summary.csv`
- `batch_run_status.csv`
- `ONLINE_ONLY_MULTIORGANISM_REVIEW.md`
- `organism_runs/<organism_key>/` with each isolated individual run

## Provenance rules

Each individual run uses `allow_demo_data=False` through the generic online-only function. Online
evidence is kept separate from `user_curated`, packaged demo data and curated snapshots. The batch
counts any user-supplied layers found in provenance and marks them visibly; it never reclassifies
them as online evidence.

Failed, timed-out, empty, disabled or unavailable providers remain explicit in the provider and
layer audit. `unresolved` means no usable matched evidence was retrieved. It is not provider
success and is not negative biological evidence.

## Limitations and next step

Provider availability, taxonomy mapping and response completeness can differ by organism and by
execution time. A successful batch demonstrates workflow portability and auditability, not target
efficacy. The next step should select the strongest completed organism as the manuscript demo and
retain the remaining organisms as complementary external validation, while adding providers only
through the existing layer resolver contract.
