# Supplementary Validation

## Internal Validation Scope

Internal validation checks the computational behavior of the publication package. It reviews deterministic ranking, score separation, provenance preservation, evolutionary risk warnings, conservative language, sensitivity availability, baseline availability, minimum manuscript columns and offline compatibility.

## Priority and Confidence Separation

The validation explicitly checks that `therapeutic_priority_score` and `evidence_confidence_score` both exist and remain distinct. This prevents evidence confidence from becoming an uncritical ranking signal.

## Evolutionary Risk

Candidates with high `evolutionary_escape_risk_score` must be penalized or warned. Unknown or insufficient evidence must not be rewritten as low risk.

## Baseline and Sensitivity Checks

Baseline comparison and sensitivity summaries are included to support internal review of ranking behavior. These checks are useful for software validation but do not constitute external biological confirmation.

## Reproduction

Run:

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

Then inspect `publication_internal_validation.md`, `publication_internal_validation_summary.csv` and the generated figures.
