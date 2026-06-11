# Final Publication Release Check

Target tag: `v0.1.0-publication`

Do not create the final tag until manually approved.

## Required Files

- [ ] `README.md` present and publication-ready.
- [ ] `CITATION.cff` present.
- [ ] `CHANGELOG.md` present.
- [ ] Release notes present at `docs/release_notes_v0_1_0_publication.md`.
- [ ] `LICENSE` present with Apache License 2.0 for project code.
- [ ] Project code is licensed under Apache License 2.0. Dependency license and security review remain release requirements.
- [ ] Snakemake remains outside core dependencies and is documented as an optional workflow dependency.

## Documentation Readiness

- [ ] Demo readiness documented.
- [ ] Final demo execution validation documented at `docs/final_demo_execution_validation.md`.
- [ ] Demo expected outputs manifest documented at `docs/demo_expected_outputs_manifest.md`.
- [ ] Publication evidence indexed.
- [ ] GUI module closure documented.
- [ ] Conservative interpretation documented.
- [ ] Manuscript artifact map documented.
- [ ] Manuscript figure/table specifications documented at `docs/manuscript_figure_table_specifications.md`.
- [ ] Software release readiness checklist documented.
- [ ] Release decision documented at `docs/v0_1_0_publication_release_decision.md`.

## Validation Readiness

- [ ] Full offline suite passing with `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q`.
- [ ] `config/taxon_resolution_cache.json` clean or reverted after tests.
- [ ] No unexpected changes in `results/`, `data_processed/` or `data_sessions/`.
- [ ] Final tag not yet created unless manual approval has been given.

## Pre-publication Repository Audit Requirements

- [ ] Pre-publication repository audit documented at `docs/pre_publication_repository_audit.md`.
- [ ] Public release exclusion policy documented at `docs/public_release_exclusion_policy.md`.
- [ ] AI-use transparency statement documented at `docs/ai_use_transparency_statement.md`.
- [ ] Repository hygiene checklist documented at `docs/repository_hygiene_checklist.md`.
- [ ] License and dependency audit documented at `docs/license_and_dependency_audit.md`.
- [ ] Dependency security review documented at `docs/dependency_security_review.md`.
- [ ] Optional workflow transitive license/security review remains pending before public workflow distribution.

Final public release is blocked until:

- project code license is Apache License 2.0;
- dependency review is complete;
- optional workflow dependency review is complete before public workflow distribution;
- sensitive data review is complete;
- internal prompts/logs are removed or excluded;
- AI-use transparency statement is reviewed;
- human approval is given.

## Interpretation Boundaries

- [ ] No clinical validation is claimed.
- [ ] No experimental validation is claimed.
- [ ] Workflow validation is not biological validation.
- [ ] `user_curated` evidence is curator-provided and not automatically externally validated.
- [ ] Ranked candidates do not confirm therapeutic validity.
