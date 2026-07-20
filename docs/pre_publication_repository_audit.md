# Pre-Publication Repository Audit

## Purpose

This audit defines publication-safety requirements before making the repository public or creating the final public release tag `v0.1.0`. It is a legal, privacy, dependency, provenance, internal-log and AI-use transparency review. It is not a scientific validation layer.

The repository owner has given final human approval for release. The tag remains blocked until the exact release-candidate commit passes the required automated checks and is merged into `main`.

## 1. Licensing

Project code is licensed under Apache License 2.0. Third-party dependencies, databases, provider content and external tools remain governed by their respective licenses and terms of use.

Before public release:

- confirm the Apache License 2.0 project-code license is present in `LICENSE`;
- confirm documentation, data templates, examples and code are covered by the intended project license or explicitly documented exceptions;
- review third-party dependencies for license obligations;
- document constraints that affect redistribution.

## 2. Dependency Audit

Dependencies must be reviewed before public release. The review includes:

- dependency license compatibility;
- security and vulnerability considerations;
- separation of optional dependencies from core requirements;
- reproducibility of dependency installation.

Dependency auditing is a release-readiness requirement, not scientific validation.

For `v0.1.0`, Snakemake is an optional workflow dependency, not a core dependency. Optional workflow dependencies remain subject to their own transitive license and security review.

## 3. Similarity And Third-Party Code Provenance

Code and documentation must be reviewed for fragments copied from third-party sources. Generated or AI-assisted text and code also require human review.

Suspiciously similar fragments must be rewritten, attributed, removed or documented. This applies to code, comments, tests, documentation, examples and generated manuscript-support text.

## 4. Internal Prompts And Logs

Prompts, raw ChatGPT or Codex transcripts, internal planning notes, temporary logs and local debug output must not be included unless intentionally documented, scrubbed and approved.

Internal prompts and logs may contain implementation rationale, private paths, accidental personal data or unsupported claims. They must be removed or excluded from public packaging unless explicitly needed and reviewed.

## 5. Sensitive Data

The release review covers:

- names and personal identifiers;
- emails, phone numbers and addresses;
- patient or confidential clinical data;
- institutional confidential data;
- credentials, API keys, tokens and passwords;
- private paths and local usernames.

Sensitive or restricted data must be removed or excluded before public release.

## 6. Data And Result Directories

`results/`, `data_processed/`, `data_sessions/`, caches and temporary outputs must be reviewed before public release. The public release may include only safe synthetic demo data, fixtures and intentionally documented examples.

Real datasets, unpublished datasets, non-consented datasets and uncontrolled generated outputs must not be published. Excluding a file for publication safety does not imply that the file is scientifically invalid.

## 7. AI-Use Transparency

An AI-use transparency statement is included for public release. AI assistance may have been used for drafting, coding, documentation, tests or refactoring, but all outputs remain subject to human review.

AI-use disclosure does not replace authorship, validation, licensing, privacy review or scientific responsibility.

## 8. Scientific And Clinical Limitations

The public release preserves these boundaries:

- no clinical validation;
- no experimental validation;
- no therapeutic-target validation;
- no biological validation by workflow artifacts alone;
- scoring is prioritization only;
- `user_curated` evidence is curator-provided, not automatic external validation;
- `therapeutic_priority_score` and `evidence_confidence_score` remain separate;
- the theoretical model remains under active review by our team of collaborators and is provisional.

## 9. Release Decision

Final human approval is given. The final public tag `v0.1.0` remains blocked until:

- the exact release-candidate commit passes the security and history audit;
- the strict complete suite passes;
- online-provider contracts pass;
- the clean-clone Quick Start passes;
- the public-release inventory passes;
- the pull request is merged into `main`.

Do not create the final public release tag before those checks are complete. Once they pass, create `v0.1.0` on the merged release commit.
