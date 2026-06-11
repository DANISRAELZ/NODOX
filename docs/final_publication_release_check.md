# Final Publication Release Check

Target tag: `v0.1.0-publication`

Do not create the final tag until manually approved.

## Required Files

- [ ] `README.md` present and publication-ready.
- [ ] `CITATION.cff` present.
- [ ] `CHANGELOG.md` present.
- [ ] Release notes present at `docs/release_notes_v0_1_0_publication.md`.
- [ ] `LICENSE` present, or license pending review before public distribution is stated clearly.

## Documentation Readiness

- [ ] Demo readiness documented.
- [ ] Publication evidence indexed.
- [ ] GUI module closure documented.
- [ ] Conservative interpretation documented.
- [ ] Manuscript artifact map documented.
- [ ] Software release readiness checklist documented.

## Validation Readiness

- [ ] Full offline suite passing with `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q`.
- [ ] `config/taxon_resolution_cache.json` clean or reverted after tests.
- [ ] No unexpected changes in `results/`, `data_processed/` or `data_sessions/`.
- [ ] Final tag not yet created unless manual approval has been given.

## Interpretation Boundaries

- [ ] No clinical validation is claimed.
- [ ] No experimental validation is claimed.
- [ ] Workflow validation is not biological validation.
- [ ] `user_curated` evidence is curator-provided and not automatically externally validated.
- [ ] Ranked candidates do not confirm therapeutic validity.
