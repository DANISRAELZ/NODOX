# GUI Publication Review Guide

## Purpose

The Streamlit GUI is an optional local interface for onboarding `user_curated` datasets and reviewing existing publication results. It is a review interface, not a clinical predictor and not an automated scoring runner.

## How to Run

Streamlit is optional. Install it only when you want to use the GUI:

```bash
python -m pip install streamlit
streamlit run apps/user_curated_onboarding_app.py
```

The repository can still be imported and tested without Streamlit installed.

## What the GUI Can Do

- Create local `user_curated_staging/` folders.
- Review manifest fields and local evidence completeness.
- Show a conservative quality gate before any future scoring.
- Build an expert review summary.
- Review manual approval JSON for possible future controlled scoring.
- Review existing `results/publication_package/` tables and figures in read-only mode.
- Explore candidates from publication tables using the Candidate explorer.

## What the GUI Does Not Do

- It does not execute scoring.
- It does not execute the pipeline.
- It does not execute Snakemake.
- It does not regenerate `publication_package`.
- It does not modify `results/`, `data_processed/` or `data_sessions/`.
- It does not provide experimental, pharmacological or clinical confirmation.

## Reviewing the Publication Package

The section `8. Revisar resultados publicables` reads existing files from:

```text
results/publication_package/
```

It summarizes expected tables, manifest status, README availability and figures in:

```text
results/publication_package/figures/
```

Missing tables or figures are reported as warnings. The GUI should not fail just because a publication artifact is absent.

## Candidate Explorer

The Candidate explorer reads `publication_table_1_top_candidates.csv` and combines available information from score decomposition, evolutionary risk, sensitivity stability, evidence provenance and baseline comparison tables. Candidate selection uses `gene`, `protein_id` or a fallback label when columns are missing.

For each selected candidate, the GUI shows:

- rank, gene, protein ID, product, organism and therapeutic role when available;
- `meta_priority_score`;
- `therapeutic_priority_score`;
- `evidence_confidence_score`;
- `functional_node_score`;
- `functional_node_theory_score` when available;
- `evolutionary_escape_risk_score`;
- `evolutionary_escape_penalty_applied`;
- interpretation warning, drivers, missing evidence flags, provenance status, ranking stability and baseline comparison when available.

## Score Interpretation

`therapeutic_priority_score` prioritizes computational hypotheses. `evidence_confidence_score` reports evidence support and interpretability constraints. A high therapeutic priority score does not imply high evidence confidence. `evolutionary_escape_risk_score` should remain visible because risk, redundancy or compensation concerns can limit interpretation.

Labels such as `demo_only`, `preliminary`, `proxy`, `missing`, `not_assessed` and `insufficient_evidence` must remain visible.

## Conservative Warning

Candidate-level results should be interpreted as computationally prioritized hypotheses requiring independent validation. They do not represent experimental, pharmacological or clinical confirmation.

## Regenerating the Publication Package Outside the GUI

Regenerate the package from the command line, outside the GUI:

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

The GUI only reviews the existing output.
