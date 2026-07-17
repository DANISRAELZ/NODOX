# Public Release File Inclusion Review

## Purpose

This document defines public-release file inclusion categories for `v0.1.0-publication`. It is a publication-safety review and does not change scientific interpretation.

## Safe/Expected

These categories are expected in the public release when reviewed:

- source code;
- tests;
- documentation;
- safe fixtures;
- safe demo examples;
- `README.md`;
- `CITATION.cff`;
- `LICENSE`;
- `CHANGELOG.md`;
- release notes.

## Conditional: Review Before Inclusion

These categories require review before inclusion:

- demo outputs;
- generated publication packages;
- dependency inventories;
- manuscript artifacts;
- optional workflow files.

## Exclude Unless Explicitly Approved

These categories should be excluded unless explicitly approved:

- `.env`;
- credentials;
- raw prompts/transcripts;
- unreviewed logs;
- uncontrolled `results/`;
- uncontrolled `data_sessions/`;
- uncontrolled `data_processed/`;
- local caches;
- patient data;
- confidential institutional data;
- real unpublished datasets without consent.

## Boundary

File inclusion review prevents accidental disclosure and licensing/privacy problems. It does not provide clinical validation, experimental validation or biological validation.
