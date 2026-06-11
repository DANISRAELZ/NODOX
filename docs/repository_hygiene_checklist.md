# Repository Hygiene Checklist

## Pre-Release Hygiene

- [ ] `git status --short` clean before release.
- [ ] No unexpected modified tracked files.
- [ ] No untracked private files.
- [ ] No `.env`.
- [ ] No credentials.
- [ ] No secrets.
- [ ] No private local paths.
- [ ] No patient data.
- [ ] No confidential institutional data.
- [ ] No unreviewed prompts/logs.
- [ ] No uncontrolled results.
- [ ] No uncontrolled data_sessions.
- [ ] No uncontrolled data_processed.
- [ ] No cache metadata changes.
- [ ] LICENSE decision complete.
- [ ] Dependency licenses reviewed.
- [ ] Dependency security reviewed.
- [ ] Core install does not require Snakemake.
- [ ] Optional workflow dependencies reviewed before public workflow distribution.
- [ ] README limitations present.
- [ ] CITATION metadata reviewed.
- [ ] AI-use transparency statement present.
- [ ] Full offline suite passing.
- [ ] Final human approval before tag.

## Notes

This checklist blocks public release until publication-safety risks are reviewed. It does not add scientific validation and does not change the interpretation of scores or ranked candidates.
