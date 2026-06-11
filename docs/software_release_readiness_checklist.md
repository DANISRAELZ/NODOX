# Software Release Readiness Checklist

## Recommended Release Name

Use a conservative publication release name such as:

```text
v0.1.0-publication
```

Do not create the release tag until the final release review explicitly approves it.

## README Status

- [ ] README explains the purpose of Nodos Funcionales as a prioritization framework.
- [ ] README avoids clinical, biological or experimental validation overclaims.
- [ ] README points to demo, documentation and testing instructions.

## Installation Instructions

- [ ] Installation instructions are present and tested in a clean environment.
- [ ] Required dependencies are minimal and documented.
- [ ] Optional GUI dependencies are clearly separated from core pipeline requirements.

## Offline Reproducibility

- [ ] The offline test suite passes with `-m "not online"`.
- [ ] Demo instructions do not require internet access by default.
- [ ] Cache metadata changes are excluded from final release diffs when they only reflect refresh timestamps or counters.

## Demo Instructions

- [ ] The Pseudomonas aeruginosa publication demo is documented.
- [ ] Expected inputs and expected outputs are listed.
- [ ] `ranking_nodos.csv`, `report_phase2.md` and publication package expectations are described.

## GUI Status

- [ ] GUI module closure is documented.
- [ ] `user_curated` onboarding, quality gate, conservative review, controlled execution and run review are covered.
- [ ] Isolated GUI runs and run-local `publication_package/` behavior are documented.
- [ ] Comparison output is restricted to `review/`.

## CLI And Pipeline Status

- [ ] CLI or script entrypoints are documented.
- [ ] Controlled pipeline execution behavior is tested.
- [ ] Output locations are documented and reproducible.

## Tests

- [ ] Focal tests for new release-readiness documents pass.
- [ ] Related GUI, publication and documentation tests pass.
- [ ] Full offline suite passes.

## Documentation

- [ ] Theoretical foundation is documented.
- [ ] Scoring interpretation is documented.
- [ ] Evidence/provenance boundaries are documented.
- [ ] Publication evidence index is complete.
- [ ] Manuscript artifact map is complete.

## Citation And Release Metadata

- [ ] `CITATION.cff` exists and is current.
- [ ] `LICENSE` exists or the release notes explicitly identify the licensing gap before tagging.
- [ ] `CHANGELOG` or release notes exist.
- [ ] Version tag plan is recorded.
- [ ] Proposed version tag is `v0.1.0-publication` or a similarly conservative publication tag.

## Known Limitations

- [ ] The release states that scoring is not clinical validation.
- [ ] The release states that workflow validation is not biological or experimental validation.
- [ ] The release states that `user_curated` evidence is curator-provided and not automatically externally validated.
- [ ] Online providers, if used later, are optional and provenance-tracked.
