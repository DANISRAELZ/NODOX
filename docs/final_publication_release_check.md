# Final Publication Release Check

Target version: `0.1.0`

Target tag: `v0.1.0`

Release date: `2026-07-20`

The repository owner has authorized the merge, tag creation and public release after the final release-candidate checks pass.

## Required Files

- [x] `README.md` present and publication-ready.
- [x] `CITATION.cff` present with version `0.1.0` and release date `2026-07-20`.
- [x] `CHANGELOG.md` present.
- [x] Release notes present at `docs/release_notes_v0_1_0_publication.md`.
- [x] `LICENSE` present with Apache License 2.0 for project code.
- [x] Project code is licensed under Apache License 2.0. Third-party data and dependencies remain governed by their respective licenses and terms.
- [x] Snakemake remains outside core dependencies and is documented as an optional workflow dependency.

## Documentation Readiness

- [x] Demo readiness documented.
- [x] Final demo execution validation documented at `docs/final_demo_execution_validation.md`.
- [x] Demo expected outputs manifest documented at `docs/demo_expected_outputs_manifest.md`.
- [x] Publication evidence indexed.
- [x] GUI module closure documented.
- [x] Conservative interpretation documented.
- [x] Manuscript artifact map documented.
- [x] Manuscript figure/table specifications documented at `docs/manuscript_figure_table_specifications.md`.
- [x] Software release readiness checklist documented.
- [x] Release decision documented at `docs/v0_1_0_publication_release_decision.md`.

## Validation Readiness

- [x] Final strict complete suite passes on the release-candidate branch.
- [x] Quick Start smoke test passes from a clean GitHub Actions checkout.
- [x] Public release inventory passes with no blocked release files or personal local paths.
- [x] Security and Git-history audit passes.
- [x] Online-provider contracts and organism regressions pass under their documented policies.
- [x] `config/taxon_resolution_cache.json` is excluded from unintended test drift by the release workflows.
- [x] Release outputs, caches and local session directories are excluded or audited.
- [ ] Final tag points to the merged release commit on `main`.

## Pre-publication Repository Audit Requirements

- [x] Pre-publication repository audit documented at `docs/pre_publication_repository_audit.md`.
- [x] Public release exclusion policy documented at `docs/public_release_exclusion_policy.md`.
- [x] AI-use transparency statement documented at `docs/ai_use_transparency_statement.md`.
- [x] Repository hygiene checklist documented at `docs/repository_hygiene_checklist.md`.
- [x] License and dependency audit documented at `docs/license_and_dependency_audit.md`.
- [x] Dependency security review documented at `docs/dependency_security_review.md`.
- [x] Final public release audit documented at `docs/final_public_release_audit.md`.
- [x] Sensitive data and secret scan documented at `docs/sensitive_data_and_secret_scan.md`.
- [x] Core dependency review summary documented at `docs/core_dependency_review_summary.md`.
- [x] Public release file inclusion review documented at `docs/public_release_file_inclusion_review.md`.
- [x] Repository owner confirms release authorization and accepts the documented remaining third-party and scientific limitations.

## Interpretation Boundaries

- [x] No clinical validation is claimed.
- [x] No experimental validation is claimed.
- [x] Workflow validation is not biological validation.
- [x] `user_curated` evidence is curator-provided and not automatically externally validated.
- [x] Ranked candidates do not confirm therapeutic validity.
- [x] The theoretical model is described as provisional and under active review by our team of collaborators.

## Final Publication Sequence

1. Complete the final workflows on the exact release-candidate commit.
2. Mark the pull request ready for review.
3. Merge into `main`.
4. Create tag `v0.1.0` on the merged release commit.
5. Publish the repository and configure its public description and topics.
