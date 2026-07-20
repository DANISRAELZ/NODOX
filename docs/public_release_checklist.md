# NODOX public release checklist

This checklist must be completed before changing the repository visibility from private to public.

## Repository identity

- [ ] README title and project description consistently use NODOX.
- [ ] Repository description and topics are configured in GitHub.
- [ ] Version number and release tag agree.
- [ ] Author and institutional attribution have been reviewed.
- [ ] The Apache-2.0 license attribution is correct.
- [ ] CITATION.cff has been reviewed by the author.

## Security and privacy

- [ ] No API keys, tokens, passwords, private keys, cookies, or authorization headers are tracked.
- [ ] No `.env` or local configuration containing secrets is tracked.
- [ ] No personal Windows, WSL, Linux, or OneDrive paths are tracked.
- [ ] No patient, employee, collaborator, or other personal data are tracked.
- [ ] No private user-curated datasets or unpublished restricted datasets are tracked.
- [ ] Git history has been scanned, not only the current files.
- [ ] Any previously committed credential has been revoked and removed from history.

## Reproducibility

- [ ] Installation succeeds in a clean supported Python environment.
- [ ] Runtime and development dependencies are separated.
- [ ] The documented Quick Start succeeds from a clean clone.
- [ ] Required demo or controlled-reference data are actually included.
- [ ] Offline tests pass.
- [ ] Online tests are clearly separated and tolerate provider outages.
- [ ] External tools such as DIAMOND are documented as optional system dependencies.

## Scientific communication

- [ ] README clearly labels NODOX as exploratory scientific software.
- [ ] Demo, proxy, cache, controlled-reference, online, and user-curated evidence are distinguished.
- [ ] Limitations and validation requirements are visible near the beginning of the README.
- [ ] Example rankings are not presented as experimentally validated therapeutic claims.
- [ ] Third-party databases and their licensing or terms of use have been reviewed.

## GitHub release preparation

- [ ] A pull request from `public-release-review` to `main` has been reviewed.
- [ ] Automated tests pass on the final commit.
- [ ] A clean release tag is created after merging.
- [ ] The repository remains private until all blocking items are complete.
