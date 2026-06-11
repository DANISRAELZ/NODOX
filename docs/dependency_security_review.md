# Dependency Security Review

## Purpose

This document records the security-review boundary for dependencies before public release. It is a release-readiness safeguard, not scientific validation.

## Core Release

The core release dependency set is defined by `requirements.txt` and the core `dependencies` list in `pyproject.toml`. The core install does not require Snakemake by default.

Before public release, core dependencies should be reviewed for known vulnerabilities, version constraints and maintenance status.

## Optional Workflow Dependencies

Snakemake is an optional workflow dependency declared in `requirements-workflow.txt` and the `workflow` optional dependency group in `pyproject.toml`.

Optional workflow dependencies have separate transitive license/security review requirements. Public workflow distribution remains blocked until optional workflow dependency review is completed.

UNKNOWN Snakemake transitive dependency metadata does not block the core release when Snakemake is not part of the core install, but it remains a blocker for public workflow distribution.

## Interpretation Boundary

Dependency security review does not imply clinical validation, experimental validation or biological validation. It only supports software release readiness.
