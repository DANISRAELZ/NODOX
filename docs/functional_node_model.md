# Functional Node Model

## Scientific purpose

This phase makes the computational model explicit for publication-oriented review. Nodos Funcionales remains a therapeutic prioritization platform: it ranks candidate functional node hypotheses from local result tables and does not claim experimental, clinical or pharmacological validation.

## Variables

- `therapeutic_priority_score`: model priority for therapeutic review.
- `evidence_confidence_score`: confidence and provenance support for interpretation.
- `functional_node_score`: operational signal for node importance.
- `functional_node_theory_score`: theory-oriented functional node support.
- `evolutionary_escape_risk_score`: estimated risk that escape or compensation may weaken prioritization.
- `evolutionary_escape_penalty_applied`: explicit penalty derived from escape risk.
- `evolutionary_adjusted_meta_priority_score`: ranking score after escape penalty.
- `meta_priority_score`: integrated computational priority before the final evolutionary adjustment.
- `final_priority_rank`: deterministic rank.
- `interpretation_warning`: conservative interpretation note.

## Score separation

`meta_priority_score`, `therapeutic_priority_score` and `evidence_confidence_score` answer different questions. Therapeutic priority ranks hypotheses. Evidence confidence describes how much support and traceability should accompany interpretation. A high confidence value does not convert a hypothesis into a biological conclusion, and low evidence does not mean low risk.

## Evolutionary risk

`evolutionary_escape_risk_score` is kept visible and decomposable. High escape risk applies or preserves `evolutionary_escape_penalty_applied` and adds a warning. This prevents functional importance from hiding possible resistance, redundancy or compensation concerns.

## Data provenance

Labels such as `user_curated`, `demo`, `proxy`, `controlled`, `missing`, `not_assessed` and `not_reported` remain limitations or provenance signals. They are not converted into negative evidence, safety evidence or acceptance for testing.

## Reproduction

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

The command is offline and uses existing local files under `results/`.
