# Pre-Publication Repository Audit

## Purpose

This audit defines publication-safety requirements before making the repository public or creating the final public release tag `v0.1.0-publication`. It is a legal, privacy, dependency, provenance, internal-log and AI-use transparency review. It is not a scientific validation layer.

The final tag is blocked until the audit items below are reviewed and approved by a human maintainer.

## 1. Licensing

Project code is licensed under Apache License 2.0. Dependency license and security review remain release requirements.

Before public release:

- confirm the Apache License 2.0 project-code license is present in `LICENSE`;
- confirm whether documentation, data templates, examples and code share the same license;
- review third-party dependencies for license obligations;
- document any license constraints that affect redistribution.

## 2. Dependency Audit

Dependencies must be reviewed before public release. The review should include:

- dependency license compatibility;
- security/vulnerability review;
- whether optional dependencies are clearly separated from core requirements;
- whether dependency versions are reproducible enough for the release.

Dependency audit is a release-readiness requirement, not scientific validation.

For `v0.1.0-publication`, Snakemake is an optional workflow dependency, not a core dependency. UNKNOWN Snakemake transitive dependency metadata does not block the core release if Snakemake is not installed as core. Public workflow distribution remains blocked until optional workflow dependency review is completed.

## 3. Similarity And Third-Party Code Provenance

Before public release, review code and documentation for fragments copied from third-party sources. Generated or AI-assisted text/code should also be reviewed.

Suspiciously similar fragments should be rewritten, attributed, removed or documented. This applies to code, comments, tests, documentation, examples and generated manuscript-support text.

## 4. Internal Prompts And Logs

Search for prompts, raw ChatGPT/Codex transcripts, internal planning notes, temporary logs and local debug output. These should not be included in the public release unless intentionally documented, scrubbed and approved.

Internal prompts and logs may contain implementation rationale, private paths, accidental personal data or unsupported claims. They should be removed or excluded from public packaging unless explicitly needed and reviewed.

## 5. Sensitive Data

Search for sensitive data before public release, including:

- names;
- emails;
- phone numbers;
- addresses;
- patient data;
- clinical data;
- institutional confidential data;
- credentials;
- API keys;
- tokens;
- passwords;
- private paths;
- local usernames.

Sensitive data must be removed or excluded before public release.

## 6. Data And Result Directories

Review `results/`, `data_processed/`, `data_sessions/`, caches and temporary outputs before public release. Public release should include only safe demo data, fixtures and intentionally documented examples.

Real datasets, unpublished datasets, non-consented datasets and uncontrolled generated outputs should not be published. Excluding a file for publication safety does not imply the file is scientifically invalid.

## 7. AI-Use Transparency

Include an AI-use transparency statement before public release. AI assistance may have been used for drafting, coding, documentation, tests or refactoring, but all outputs require human review.

AI-use disclosure must not replace authorship, validation, licensing, privacy review or scientific responsibility.

## 8. Scientific And Clinical Limitations

The public release must preserve these boundaries:

- no clinical validation;
- no experimental validation;
- no therapeutic target validation;
- no biological validation by workflow artifacts alone;
- scoring is prioritization only;
- `user_curated` evidence is curator-provided, not automatic external validation;
- `therapeutic_priority_score` and `evidence_confidence_score` remain separate.

## 9. Release Decision

The final public tag `v0.1.0-publication` remains blocked until:

- license is decided;
- dependency review is complete;
- sensitive data scan is complete;
- internal prompts/logs are removed or excluded;
- AI-use transparency statement is added and reviewed;
- final human approval is given.

Do not create the final public release tag automatically.
