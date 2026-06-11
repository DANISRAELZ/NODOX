# License And Dependency Audit

## Purpose

This document records the dependency boundary for the minimum `v0.1.0-publication` core release. It does not complete the legal review and does not provide scientific, clinical or experimental validation.

Project code is licensed under Apache License 2.0. Dependency license and security review remain release requirements.

## Core Dependency Boundary

The core publication release installs from:

```text
requirements.txt
```

The core install does not require Snakemake. Snakemake is separated as an optional workflow dependency so the core runtime, GUI review surfaces and offline tests can remain independent of workflow-engine installation by default.

## Optional Workflow Dependency

Snakemake remains available for users who want workflow execution support:

```text
requirements-workflow.txt
```

or the optional project extra:

```text
.[workflow]
```

Optional workflow dependencies have separate transitive license/security review requirements. Public workflow distribution remains blocked until optional workflow dependency review is completed.

UNKNOWN Snakemake transitive dependency metadata does not block the core release if Snakemake is not installed as a core dependency. It does continue to block public workflow distribution until reviewed.

Public workflow distribution remains blocked until reviewed.

## Dependency License Inventory

`docs/dependency_license_inventory.md` reflects the current local virtual environment used to generate the inventory. It may include optional workflow/transitive packages that are not required by the core release.

Do not treat the inventory as the minimal core dependency list unless a fresh core-only environment is generated and inventoried.

## Release Boundary

Dependency audit is a release-readiness requirement, not biological validation, clinical validation or experimental validation. It does not change scoring interpretation or candidate status.
