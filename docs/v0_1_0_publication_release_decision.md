# v0.1.0-publication Release Decision

## Release Candidate

Release candidate: `v0.1.0-publication`

## Current Readiness Status

The project is ready for final human approval review as a minimum publication-ready software package. The final git tag should not be created automatically. No automatic tag creation is approved in this phase.

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
- Offline deterministic test coverage for release-readiness documents.

## Pending Components

- License decision before public distribution.
- Optional final manual demo run using `examples/pseudomonas_aeruginosa_publication_demo`.
- Optional manuscript figure generation from the figure/table specifications.
- Final human approval before tag creation.

## Release Boundary

This release is a minimum publication-ready software package. It is not a clinically validated platform, not an experimentally validated platform and not a biological validation package. It does not validate therapeutic targets or confirm therapeutic validity for ranked candidates.

## Tagging Instruction After Approval

After final human approval only, the suggested tag command is:

```bash
git tag v0.1.0-publication
```

Do not run this command automatically.
