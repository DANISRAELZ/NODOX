# Manuscript Artifact Map

## Purpose

This map links software outputs and repository documents to manuscript figures, tables and supplementary materials. These are manuscript-support artifacts and not biological validation by themselves.

## Figures

| Manuscript artifact | Suggested source | Purpose | Boundary |
| --- | --- | --- | --- |
| Figure 1: Functional Nodes conceptual framework | `docs/theory_of_functional_nodes.md`, `docs/functional_nodes_theory_operationalization.md` | Explain the theoretical model and why nodes are prioritized. | Conceptual figures do not validate targets experimentally. |
| Figure 2: user_curated workflow | `docs/user_curated_operational_flow.md`, `docs/user_curated_gui_onboarding.md` | Show curator-provided input flow, checks and provenance. | `user_curated` evidence is not automatically external validation. |
| Figure 3: GUI execution and run-review workflow | `docs/gui_controlled_pipeline_execution.md`, `docs/gui_run_review_publication_validation.md` | Show controlled execution, logs, outputs, review and comparison. | GUI review demonstrates workflow auditability, not clinical validation. |
| Figure 4 or supplementary figure: isolated publication package structure | `docs/gui_run_review_publication_validation.md`, `docs/publication_results_package.md` | Show separation between `outputs/`, `publication_package/` and `review/`. | Package structure is a reporting artifact, not biological confirmation. |

## Tables

| Manuscript artifact | Suggested source | Purpose | Boundary |
| --- | --- | --- | --- |
| Table 1: model variables and interpretation | `docs/scoring.md`, `docs/therapeutic_priority_decomposition_phase.md` | Define variables including `therapeutic_priority_score` and `evidence_confidence_score`. | Priority and confidence must remain separate. |
| Table 2: evidence/provenance classes | `docs/evidence_hierarchy.md`, `docs/evidence_strength_framework.md`, `docs/layer_source_audit.md` | Explain provenance, evidence classes and source limitations. | Provenance class does not equal experimental validation. |
| Table 3: tests and validation boundaries | `docs/testing_strategy.md`, `docs/publication_internal_validation.md` | Summarize deterministic tests and what they validate. | Software tests do not validate biological truth. |
| Table 4: demo outputs and interpretation | `examples/pseudomonas_aeruginosa_publication_demo/expected_tables/`, `docs/final_reproducible_demo_readiness.md` | Present expected demo outputs and conservative interpretation. | Demo outputs remain computational hypotheses. |

## Supplementary Material

- Supplementary material: reproducibility checklist from `docs/software_release_readiness_checklist.md`.
- Supplementary material: GUI workflow validation from `docs/gui_run_review_publication_validation.md`.
- Supplementary material: publication evidence index from `docs/publication_evidence_index.md`.
- Supplementary material: expected Pseudomonas aeruginosa demo tables from `examples/pseudomonas_aeruginosa_publication_demo/expected_tables/`.

## Interpretation Boundary

Figures and tables are manuscript-support artifacts. They document software design, reproducibility, provenance and workflow validation. They do not establish biological validation, clinical validation, therapeutic efficacy, host safety or experimental confirmation by themselves.
