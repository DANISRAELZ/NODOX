# Final Reproducible Demo Readiness

## Purpose

The final publication demo should show that the project can run from controlled local inputs, produce expected outputs and preserve conservative interpretation boundaries. The preferred demo is the existing `Pseudomonas aeruginosa` user-curated publication demo.

This demo is about reproducibility and software workflow readiness. It does not establish biological validation, clinical validation or experimental validation.

## Expected Input Directory

Use the existing demo directory:

```text
examples/pseudomonas_aeruginosa_publication_demo/
```

Expected inputs live under:

```text
examples/pseudomonas_aeruginosa_publication_demo/input/
```

Stable input files include:

- `manifest.yaml`
- `gene_list.csv`
- `manual_curation.csv`
- `evidence_quality.csv`
- `provenance.yaml`
- `notes.md`

## Expected Entrypoint

The demo provides shell entrypoints:

```text
examples/pseudomonas_aeruginosa_publication_demo/run_demo.ps1
examples/pseudomonas_aeruginosa_publication_demo/run_demo.sh
```

The publication release should document the exact command used on Windows and Unix-like systems. The demo should remain offline unless a future protocol explicitly labels optional online enrichment.

## Expected Outputs

Expected reference outputs are documented under:

```text
examples/pseudomonas_aeruginosa_publication_demo/expected_tables/
examples/pseudomonas_aeruginosa_publication_demo/expected_outputs/
```

The expected ranking file is:

```text
ranking_nodos.csv
```

The expected report file is:

```text
report_phase2.md
```

The expected publication package for a final demo run should include the same manuscript-oriented tables and figures described by the publication package builder and GUI review documents. For GUI-generated runs, the publication package must remain run-local under:

```text
results/gui_runs/<run_id>/publication_package/
```

For non-GUI CLI demos, publication package paths must be documented before release and must not overwrite controlled reference artifacts without explicit intent.

## Conservative Interpretation

The demo can support claims about reproducibility, input handling, output generation, reporting and reviewability. It must not be described as proof that any candidate is a validated therapeutic target.

`therapeutic_priority_score` ranks computational therapeutic-priority hypotheses. `evidence_confidence_score` describes evidence support and interpretability limits. `user_curated` evidence is curator-provided and not automatically external validation.

## Limitations

The Pseudomonas aeruginosa demo is a controlled software demonstration. It does not establish biological validation, clinical validation or experimental validation. It also does not replace wet-lab testing, pharmacological evaluation, host-safety assessment or organism-specific expert review.
