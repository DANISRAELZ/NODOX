# Publication Release Notes - 2026-06-10

## Release Scope

This release prepares Nodos Functional for academic manuscript and publication package review. It consolidates the explicit computational model, baseline comparison, internal validation, interpretative figures and manuscript-facing documentation.

## Added

- Explicit functional node publication model.
- Reproducible publication package builder.
- Baseline comparison table and report.
- Internal validation table and report.
- Interpretative PNG and SVG figures.
- Manuscript draft and manuscript table/figure descriptions.
- Supplementary methods, tables and validation notes.
- Minimal editable `CITATION.cff`.

## Interpretation Boundary

The release reports computationally prioritized hypotheses requiring independent validation. It does not provide experimental, pharmacological or clinical confirmation.

## Reproducibility

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

## Suggested Tag

`publication-manuscript-materials-2026-06-10`
