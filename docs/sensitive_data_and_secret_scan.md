# Sensitive Data And Secret Scan

## Purpose

This document defines a conservative lightweight repository-level scan before public release. No full external secret scanner is claimed here; final human review remains required.

## Scan Scope

Review for:

- API keys;
- tokens;
- passwords;
- `.env`;
- private keys;
- secrets;
- personal emails;
- phone numbers;
- local machine paths;
- patient data;
- clinical confidential data;
- institutional confidential data;
- internal prompts;
- raw ChatGPT/Codex transcripts;
- unreviewed logs;
- uncontrolled `results/`;
- uncontrolled `data_sessions/`;
- uncontrolled `data_processed/`;
- caches and temporary outputs.

## Lightweight Checks

The lightweight static checks should avoid binary files, virtual environments and large generated outputs. They can verify that no root `.env` file exists, that obvious secret filenames are not part of the release path, and that final release documents still require human approval.

## Release Boundary

This scan supports publication safety. It does not establish clinical validation, experimental validation, biological validation or therapeutic validity.

The public release remains blocked until sensitive data/secrets and internal prompts/logs are reviewed by a human maintainer.
