# Changelog

## v0.1.0 - 2026-07-20

Initial public release of NODOX, an exploratory and publication-oriented workflow for explainable prioritization of bacterial therapeutic-target hypotheses.

Included:

- Theory-first Functional Nodes framework for computational prioritization.
- `user_curated` input workflow with explicit provenance and quality checks.
- Conservative interpretation rules for ranked candidates.
- Offline reproducibility through deterministic local tests and demos.
- GUI onboarding, controlled execution and run-review workflow.
- Isolated GUI runs under `results/gui_runs/<run_id>/`.
- Run-local `publication_package/` behavior for isolated GUI runs.
- Publication-readiness documentation, evidence index, demo readiness notes, manuscript artifact map and final release checklist.
- Multiorganism architecture and optional online evidence providers.
- Explicit distinction between software reproducibility and scientific validation.

Known limitations:

- No clinical validation is provided.
- No experimental validation is provided.
- Workflow validation is not biological validation.
- Ranked candidates are computationally prioritized hypotheses and do not confirm therapeutic validity.
- `user_curated` evidence is curator-provided and not automatically externally validated.
- The theoretical model remains under active review by our team of collaborators and may change as that review progresses.

License:

- Project code is distributed under Apache License 2.0.
- Third-party data and provider terms remain governed by their respective licenses and terms of use.
