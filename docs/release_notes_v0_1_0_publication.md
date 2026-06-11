# Release Notes: v0.1.0-publication

Release date: 2026-06-11

## Release Scope

`v0.1.0-publication` is a minimum publication-ready release candidate for Nodos Funcionales. It packages the theory-first prioritization workflow, user-curated input path, conservative interpretation rules, GUI-assisted review/execution workflow, isolated publication package behavior and release-readiness documentation needed for manuscript/demo reporting.

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
- Pseudomonas aeruginosa publication demo readiness documentation.
- Publication evidence index, manuscript artifact map, release checklist and master readiness index.

## Not Included

- No new GUI features beyond the existing publication-ready workflow.
- No clinical deployment, authentication or multi-user server mode.
- No deep learning layer.
- No mandatory online queries.
- No new biological scoring logic.
- No claim that candidates have confirmed therapeutic validity.

## Validation Status

The release is validated as a software workflow through offline deterministic tests, documentation contracts and controlled demo readiness checks. This is workflow validation, not biological validation.

## Intended Use

The intended use is research-oriented computational prioritization, evidence integration, reproducible demo execution and manuscript-methods reporting. Outputs should guide downstream review and validation planning.

## Not Intended Use

This release is not intended for clinical decision-making, diagnosis, antimicrobial prescription, host-safety determination or therapeutic target confirmation.

## Limitations

- No clinical validation is provided.
- No experimental validation is provided.
- No pharmacological validation is provided.
- `user_curated` evidence is curator-provided and not automatically external validation.
- Scoring requires downstream biological and experimental validation before biological or therapeutic claims.
- Ranked candidates remain computationally prioritized hypotheses and do not confirm therapeutic validity.
- Project code is licensed under Apache License 2.0. Dependency license and security review remain release requirements.

## Known Next Steps After Release

- Confirm public license selection.
- Finalize author metadata when available.
- Prepare manuscript figures and tables from the artifact map.
- Run the final demo and archive exact release outputs.
- Create the `v0.1.0-publication` tag only after manual approval.
