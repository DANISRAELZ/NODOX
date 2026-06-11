# Public Release Exclusion Policy

## Purpose

This policy defines files and directories that should normally be excluded from public release unless explicitly reviewed and approved. Exclusion is a publication-safety policy. It does not imply that excluded files are scientifically invalid.

The goal is to prevent accidental disclosure, licensing issues, privacy issues and uncontrolled redistribution of generated or sensitive content. This policy prevents accidental disclosure by requiring review before public packaging.

## Always Exclude Or Review Before Public Release

Review or exclude:

- `.env`
- credentials
- API keys
- tokens
- passwords
- private config files
- local machine paths
- personal emails
- patient or clinical data
- real institutional data
- internal prompts
- raw ChatGPT/Codex transcripts
- unreviewed logs
- caches
- temporary outputs
- uncontrolled `results/`
- uncontrolled `data_sessions/`
- uncontrolled `data_processed/`
- large generated artifacts
- unpublished real datasets
- non-consented datasets

## Allowed Only If Reviewed

These may be included only after review:

- fixtures
- toy/demo datasets
- publication demo inputs
- expected outputs generated from safe demo data
- documentation examples
- tests

## Review Rule

When unsure, exclude the file from public release until a human maintainer confirms that it is safe, licensed, non-sensitive and intentionally part of the public package.
