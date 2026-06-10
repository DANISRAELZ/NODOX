# Supplementary Methods

## Extended Model Description

Nodos Functional integrates candidate-level evidence into explicit scores. The publication model preserves or computes `meta_priority_score`, `therapeutic_priority_score`, `evidence_confidence_score`, `functional_node_score`, `functional_node_theory_score`, `evolutionary_escape_risk_score`, `evolutionary_escape_penalty_applied` and `evolutionary_adjusted_meta_priority_score`.

The default configuration is stored in `FunctionalNodeModelConfig`. The current publication demo uses interpretable weights for antibiotic target signal, antivirulence signal, functional node signal, selectivity, clinical context and evolutionary penalty. Evidence confidence is preserved as an interpretation layer and does not automatically increase therapeutic priority.

## Conservative Rules

- A score high in the model is a prioritization signal, not independent confirmation.
- `therapeutic_priority_score` and `evidence_confidence_score` remain separate.
- High `evolutionary_escape_risk_score` triggers warning or penalty.
- Insufficient evidence is not converted into low risk.
- `demo_only`, `preliminary`, `proxy`, `missing`, `not_assessed` and `insufficient_evidence` labels remain visible.

## Baseline Comparison

The baseline comparison ranks candidates by antibiotic target score, functional node score and an unweighted mean. These baselines are internal references used to understand how the integrated model differs from simpler ranking rules.

## Reproducing the Publication Package

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

The command operates offline from local result tables.
