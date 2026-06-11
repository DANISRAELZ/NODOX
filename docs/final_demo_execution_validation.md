# Final Demo Execution Validation

## Purpose

The final publication demo validates the practical software path for Nodos Funcionales as an offline-capable, reproducible and publication-oriented workflow. The preferred demo is the existing Pseudomonas aeruginosa demo:

```text
examples/pseudomonas_aeruginosa_publication_demo/
```

This document defines what should be checked before using the demo as manuscript-support evidence.

## Expected Input Location

The expected input directory is:

```text
examples/pseudomonas_aeruginosa_publication_demo/input/
```

Stable input files include `manifest.yaml`, `gene_list.csv`, `manual_curation.csv`, `evidence_quality.csv`, `provenance.yaml` and `notes.md`.

## Safe Offline Execution Path

The demo provides local entrypoints:

```text
examples/pseudomonas_aeruginosa_publication_demo/run_demo.ps1
examples/pseudomonas_aeruginosa_publication_demo/run_demo.sh
```

For release review, a safe offline execution path means using the local scripts and local curated inputs only, without mandatory online provider calls. If a final manual demo run is performed, record the exact command, environment and output directory in release notes.

## Expected Outputs

Reference outputs are documented under:

```text
examples/pseudomonas_aeruginosa_publication_demo/expected_tables/
examples/pseudomonas_aeruginosa_publication_demo/expected_outputs/
```

Expected artifacts include:

- `ranking_nodos.csv`
- `report_phase2.md` or an equivalent report
- `candidate_explanations_simple.csv`
- `candidate_audit.csv`
- `evidence_strength_audit.csv`
- `layer_resolution_summary.csv`
- `publication_package/` for a generated publication package

For GUI-generated runs, any publication package must remain under:

```text
results/gui_runs/<run_id>/publication_package/
```

Review comparison output must remain under:

```text
results/gui_runs/<run_id>/review/
```

## What The Demo Proves

The demo can support claims about:

- workflow reproducibility;
- input/output traceability;
- publication package structure;
- offline execution readiness;
- conservative manuscript/demo reporting.

## What The Demo Does Not Prove

The demo provides no biological validation, no clinical validation and no experimental validation. It does not validate therapeutic targets and does not confirm therapeutic validity for ranked candidates.

## Conservative Interpretation

`therapeutic_priority_score` ranks computational prioritization hypotheses. `evidence_confidence_score` describes evidence support and interpretability constraints. `user_curated` evidence is curator-provided and is not automatic external validation.

Candidate ranking requires downstream biological and experimental validation before biological, clinical or therapeutic claims.
