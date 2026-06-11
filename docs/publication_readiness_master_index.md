# Publication Readiness Master Index

## Purpose

This master index links the closure documents for the minimum publication-ready software release. It is a navigation layer for final demo, manuscript, release tag and software citation preparation.

## Readiness Documents

- GUI module closure: `docs/gui_module_closure_2026_06_11.md`
- Publication evidence index: `docs/publication_evidence_index.md`
- Final reproducible demo readiness: `docs/final_reproducible_demo_readiness.md`
- Software release readiness checklist: `docs/software_release_readiness_checklist.md`
- Manuscript artifact map: `docs/manuscript_artifact_map.md`
- GUI run-review publication validation: `docs/gui_run_review_publication_validation.md`
- Final demo execution validation: `docs/final_demo_execution_validation.md`
- Demo expected outputs manifest: `docs/demo_expected_outputs_manifest.md`
- Manuscript figure/table specifications: `docs/manuscript_figure_table_specifications.md`
- v0.1.0 publication release decision: `docs/v0_1_0_publication_release_decision.md`

## Remaining Path To Final Demo

The final demo should use the existing Pseudomonas aeruginosa publication demo, verify expected inputs and outputs, and report `ranking_nodos.csv`, `report_phase2.md` and publication package expectations with conservative interpretation.

The final demo execution validation and demo expected outputs manifest define the lightweight, offline checks needed before using the demo as manuscript-support evidence.

## Remaining Path To Manuscript

The manuscript can use the artifact map to assemble conceptual figures, workflow figures, model-variable tables, provenance tables, test-boundary tables and demo-output tables.

The manuscript figure/table specifications define concrete content requirements for Figures 1-4 and Tables 1-4 without generating new image files.

## Remaining Path To Release Tag

Before tagging, complete the release readiness checklist, run focal tests, run related GUI/publication tests and run the full offline suite. A conservative candidate tag is:

```text
v0.1.0-publication
```

The requested phase tag can be:

```text
publication-readiness-closure-2026-06-11
```

Do not create tags until explicitly instructed.

The release decision document records that the project is ready for final human approval review, with dependency license/security review, optional final manual demo run and optional manuscript figure generation still pending.

## Remaining Path To Software Citation

Confirm `CITATION.cff`, release notes, Apache License 2.0 project-code status, dependency license/security review and version tag before final publication release. The citation should describe Nodos Funcionales as prioritization software and must not imply clinical, biological or experimental validation.
