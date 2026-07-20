# v0.1.0 Release Decision

## Release Candidate

Final release version: `0.1.0`

Final release tag: `v0.1.0`

Release date: `2026-07-20`

## Approval Status

The repository owner approved the final release version, publication date, merge, tag creation and public release. No ORCID is included because one is not yet available.

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
- Manuscript figure and table specifications.
- Release notes and final release checklist.
- Final public release audit workflow.
- Sensitive-data and secret scanning.
- Core dependency review summary.
- Public-release file inclusion review.
- Strict complete pytest suite.
- Clean-clone Quick Start smoke test.
- Public-release inventory workflow.

## Scientific Status

This release is a publication-oriented research software package. It provides no clinical validation, no experimental validation and no biological validation by itself. It does not validate therapeutic targets or confirm therapeutic validity for ranked candidates.

The theoretical model underlying NODOX remains under active review by our team of collaborators. Its concepts, assumptions, variables and scoring interpretation are provisional and may change as that review progresses.

## Dependency Boundary

The core release does not require Snakemake by default. Snakemake remains an optional workflow dependency through `requirements-workflow.txt` and the `workflow` optional dependency group. Optional workflow dependencies remain subject to their own transitive license and security review.

Project code is licensed under Apache License 2.0. Third-party databases, provider content and external tools remain governed by their respective licenses and terms of use.

## Tagging Instruction

After the final release-candidate checks pass and the pull request is merged into `main`, create the tag:

```bash
git tag v0.1.0
```

The tag must point to the merged release commit on `main`.
