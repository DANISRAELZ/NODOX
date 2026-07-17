# Core Dependency Review Summary

## Purpose

This summary distinguishes the dependency sets relevant to `v0.1.0-publication`. It does not invent license conclusions and does not complete the dependency review.

## Dependency Sets

Core dependencies are declared in:

- `requirements.txt`
- the core `dependencies` list in `pyproject.toml`

Optional workflow dependencies are declared in:

- `requirements-workflow.txt`
- the `workflow` optional dependency group in `pyproject.toml`

The local virtual environment inventory is documented in:

- `docs/dependency_license_inventory.md`

That inventory may include transitive dependencies, optional workflow dependencies and dev/test dependencies that are not part of a minimal core-only install.

## Snakemake Boundary

Snakemake is an optional workflow dependency, not core. Snakemake-related UNKNOWN metadata does not block the core release by default when Snakemake is not installed as a core dependency.

Optional workflow distribution remains blocked pending separate review of Snakemake and its transitive dependencies.

## Remaining Review Requirements

- Core dependency review must still be completed or explicitly accepted by human approval.
- Core dependency security scan must be completed or explicitly accepted by human approval.
- Optional workflow dependency review must be completed before public workflow distribution.

Dependency review is not scientific validation, clinical validation or experimental validation.
