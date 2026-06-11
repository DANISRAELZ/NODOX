# GUI Module Closure 2026-06-11

## Closure Statement

The GUI module is considered complete for the current internal publication-ready workflow. It is ready to support local `user_curated` onboarding, conservative review, controlled execution and run-review activities needed for manuscript/demo preparation.

This closure does not mean the GUI is a commercial-grade deployment, an authenticated multi-user server, a clinical decision system or a source of biological validation.

## Covered Workflow

The closed GUI workflow covers:

- `user_curated` onboarding and local staging guidance.
- A quality gate that surfaces missing, proxy, preliminary or insufficient evidence.
- Expert review and conservative interpretation before scoring is treated as reportable.
- Controlled pipeline execution through the existing runner.
- Isolated GUI runs under `results/gui_runs/<run_id>/`.
- Review of logs and outputs from the selected isolated run.
- Generation or review of a run-local `publication_package/`.
- Comparison against the base publication package with comparison output restricted to `review/`.

## Publication Boundary

The GUI supports software-methods evidence: reproducible local execution, isolation, reviewability and conservative reporting. It provides no clinical validation, no experimental validation, no pharmacological validation and no biological confirmation.

All candidate rankings remain computationally prioritized hypotheses requiring independent validation. `therapeutic_priority_score` and `evidence_confidence_score` must remain separate, and `user_curated` evidence remains curator-provided rather than automatically externally validated.

## Feature Freeze Recommendation

No further GUI feature expansion is recommended before publication. Future GUI work before the publication release should be limited to:

- bug fixes;
- usability polish;
- clearer warnings or documentation;
- post-publication roadmap notes.

Major new GUI capabilities, dashboards, authentication, multi-user server mode, online-first execution and clinical interpretation features should be deferred until after the minimum publication release.

## Remaining Risks

The GUI remains an optional local interface around existing pipeline and review logic. Publication claims should describe it as a controlled local workflow, not as a production web application.
