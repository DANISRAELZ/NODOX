# NODOX public release checklist

This checklist must be completed before changing the repository visibility from private to public.

## Repository identity

- [x] README title and project description consistently use NODOX.
- [ ] Repository description and topics are configured in GitHub.
- [x] Version `0.1.0` and release tag `v0.1.0` agree.
- [x] Author attribution has been reviewed; no institutional attribution or ORCID is included.
- [x] The Apache-2.0 license attribution is correct.
- [x] `CITATION.cff` has been reviewed with release date `2026-07-20`.

## Security and privacy

- [x] No high-confidence API keys, tokens, passwords, private keys, cookies or authorization headers were detected by the automated current-tree and Git-history scan.
- [x] No `.env` or local configuration containing secrets is tracked in the release-candidate tree.
- [x] No personal Windows, WSL, Linux or OneDrive paths are tracked in the release-candidate tree.
- [x] No patient, employee or collaborator records were identified by the public inventory and repository review.
- [x] No private user-curated or unpublished restricted datasets are intentionally included in the public release tree.
- [x] Git history has been scanned, not only the current files.
- [x] No previously committed high-confidence credential was detected; credential revocation is therefore recorded as not applicable based on the available audit evidence.

## Reproducibility

- [x] Installation of development dependencies succeeds in a clean GitHub Actions Python 3.12 environment.
- [x] Runtime and development dependencies are separated.
- [x] The documented Quick Start succeeds from a clean clone.
- [x] Required demo or controlled-reference data are included as synthetic/public fixtures and are covered by the public inventory workflow.
- [x] The organism-agnostic offline tests pass.
- [x] Online tests are separated and tolerate provider outages through individual hard time limits and diagnostic classification.
- [x] External tools such as DIAMOND are documented as optional system dependencies.
- [x] The strict complete suite passes with `python -m pytest -p no:cacheprovider -q` on the release-candidate branch.

## Scientific communication

- [x] The root README clearly labels NODOX as exploratory scientific software.
- [x] The root README states that the theoretical model remains under active review by our team of collaborators, is provisional and may change.
- [x] The documentation distinguishes software-test validation from scientific validation of the theoretical model.
- [x] Demo, proxy, cache, controlled-reference, online and user-curated evidence are distinguished in the root README.
- [x] Limitations and validation requirements are visible near the beginning of the root README.
- [x] Example rankings are not presented as experimentally validated therapeutic claims.
- [x] Third-party databases and their licensing or terms of use have been reviewed and documented in `docs/third_party_data_terms_review.md`, including unresolved or conditional restrictions.

## GitHub release preparation

- [ ] The pull request from `public-release-review` to `main` has been marked ready and merged.
- [x] Automated tests pass on the release-candidate branch, including the strict complete suite.
- [ ] A clean release tag `v0.1.0` is created on the merged release commit.
- [x] The repository remains private until the remaining GitHub publication actions are complete.

## Current automated evidence

- The public-release audit has passed the security/history audit, organism-agnostic offline suite, online-provider contracts, organism regressions and strict complete pytest suite on the release-candidate branch.
- The Quick Start smoke test has passed from a clean GitHub Actions checkout.
- The public-release inventory has passed with no blocked release files or personal local paths in the release-candidate tree.
- `README_PUBLIC.md` was promoted to `README.md`; the previous technical README is preserved as `README_TECHNICAL.md`.
- Third-party data use and redistribution rules are documented, with conservative handling for VFDB, DEG, InterPro member components and NCBI third-party rights.
- The Apache-2.0 attribution is `Copyright 2026 Dan Israel Zavala Vargas and NODOX contributors`.
- The public README and `CITATION.cff` state that the theoretical model is provisional and remains under active review by our team of collaborators.
- The repository owner authorized version `0.1.0`, tag `v0.1.0`, release date `2026-07-20`, merge and public release; no ORCID is included because none is currently available.
