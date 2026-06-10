# Publication Internal Validation

## Purpose

The internal validation layer audits the publication package as a computational demonstration. It checks deterministic ranking, score separation, conservative language, provenance preservation, evolutionary risk warnings, baseline comparison and offline reproducibility.

## Interpretation

The output is a prioritized hypothesis list of candidate functional nodes. It is not experimental validation and it is not clinical recommendation. Independent validation is required before biological, pharmacological or clinical use.

## Baseline comparison

`publication_table_6_baseline_comparison.csv` compares Nodos ranking against simple baselines:

- antibiotic target score ranking;
- functional node score ranking;
- unweighted mean of antibiotic, antivirulence and functional node scores.

Large rank deltas indicate where the integrated model differs from simpler rankings. They are review prompts, not proof of superiority.

## Current limitations

- The phase uses existing local results and does not fetch online data.
- Missing or insufficient evidence remains explicitly marked.
- Sensitivity analysis is only as complete as the local `results/sensitivity_analysis.csv`.
- Baselines are simple internal references, not external biological benchmarks.

## Suggested next steps

- Add more baseline strategies only when they are interpretable.
- Expand validation summaries with manuscript-specific figures.
- Connect future external providers through the existing layer resolver, preserving source metadata.
