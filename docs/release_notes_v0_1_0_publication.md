# Release Notes: v0.1.0

Release date: 2026-07-20

## Release Scope

`v0.1.0` is the initial public release of NODOX. It packages the theory-first prioritization workflow, user-curated input path, conservative interpretation rules, GUI-assisted review and execution workflow, isolated publication-package behavior, and release-readiness documentation needed for research and manuscript-oriented use.

## Included

- Functional Nodes theory-first software architecture.
- `user_curated` onboarding, validation and provenance-oriented workflow.
- Offline-capable pipeline execution and deterministic tests.
- Conservative scoring interpretation.
- Explicit separation between `therapeutic_priority_score` and `evidence_confidence_score`.
- GUI-assisted onboarding, controlled pipeline execution, run review, log review and output review.
- Isolated GUI runs under `results/gui_runs/<run_id>/`.
- Run-local `publication_package/` generation for isolated GUI runs.
- Comparison output restricted to `review/`.
- Multiorganism workflow support.
- Optional online evidence providers with explicit provenance and outage handling.
- Publication evidence index, manuscript artifact map, release checklist and master readiness index.

## Not Included

- No clinical deployment, authentication or multi-user server mode.
- No deep learning layer.
- No mandatory online queries.
- No claim that candidates have confirmed therapeutic validity.
- No claim that the theoretical model has completed scientific validation.

## Validation Status

The release is validated as a software workflow through deterministic tests, online-provider contract tests, a strict complete suite, documentation contracts, inventory checks and a clean-clone Quick Start. This is implementation and reproducibility validation, not biological, experimental or clinical validation.

The theoretical model underlying NODOX remains under active review by our team of collaborators. Its concepts, assumptions, variables and scoring interpretation are provisional and may change as that review progresses.

## Intended Use

The intended use is research-oriented computational prioritization, evidence integration, reproducible workflow execution and manuscript-methods reporting. Outputs should guide downstream review, curation and validation planning.

## Not Intended Use

This release is not intended for clinical decision-making, diagnosis, antimicrobial prescription, host-safety determination or therapeutic-target confirmation.

## Limitations

- No clinical validation is provided.
- No experimental validation is provided.
- No pharmacological validation is provided.
- `user_curated` evidence is curator-provided and is not automatically external validation.
- Scoring requires downstream biological and experimental validation before biological or therapeutic claims.
- Ranked candidates remain computationally prioritized hypotheses and do not confirm therapeutic validity.
- External databases and provider content remain subject to their own licenses and terms of use.

## Release Identifier

Final release tag: `v0.1.0`.
