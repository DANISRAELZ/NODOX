# v0.1.0-publication Release Decision

## Release Candidate

Release candidate: `v0.1.0-publication`

## Current Readiness Status

The project is technically close to `v0.1.0-publication` and ready for final human approval review as a minimum publication-ready software package. The final git tag should not be created automatically. No automatic tag creation is approved in this phase.

## Completed Components

- Theory-first Functional Nodes documentation.
- `user_curated` workflow documentation and validation.
- Conservative interpretation boundaries.
- GUI onboarding, controlled execution and run-review closure.
- Isolated GUI run documentation under `results/gui_runs/<run_id>/`.
- Run-local `publication_package/` behavior documentation.
- Publication evidence index.
- Final demo execution validation documentation.
- Demo expected outputs manifest.
- Manuscript figure/table specifications.
- Release notes and final release checklist.
- Final public release audit.
- Sensitive data and secret scan documentation.
- Core dependency review summary.
- Public release file inclusion review.
- Offline deterministic test coverage for release-readiness documents.

## Pending Components

- Dependency license and security review before public distribution.
- Optional workflow dependency review for Snakemake and its transitive dependencies before public workflow distribution.
- Core release can proceed only after accepting or completing core dependency/security and sensitive-data review.
- Optional final manual demo run using `examples/pseudomonas_aeruginosa_publication_demo`.
- Optional manuscript figure generation from the figure/table specifications.
- Final human approval before tag creation.

## Release Boundary

This release is a minimum publication-ready software package. It provides no clinical validation, no experimental validation and no biological validation by itself. It does not validate therapeutic targets or confirm therapeutic validity for ranked candidates.

The core release does not require Snakemake by default. Snakemake remains available as an optional workflow dependency through `requirements-workflow.txt` and the `workflow` optional dependency group. UNKNOWN Snakemake transitive dependency metadata does not block the core release when Snakemake is not installed as core, but public workflow distribution remains blocked until optional workflow dependency review is completed.

Project code is licensed under Apache License 2.0. Dependency license and security review remain release requirements.

See `docs/final_public_release_audit.md`, `docs/sensitive_data_and_secret_scan.md`, `docs/core_dependency_review_summary.md` and `docs/public_release_file_inclusion_review.md` before manual tag approval.

## Tagging Instruction After Approval

After final human approval only, the suggested tag command is:

```bash
git tag v0.1.0-publication
```

Do not run this command automatically.
