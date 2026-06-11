# GUI Run-Review Publication Validation

## Purpose

This document defines a controlled, offline validation layer for the GUI run-review workflow. Its purpose is to demonstrate that isolated GUI runs can be reproduced, inspected, packaged and compared without changing the base project outputs.

This is workflow validation. It supports manuscript and demo reporting about software behavior, reproducibility boundaries and auditability. It is not biological validation, not experimental validation, not pharmacological validation and not clinical validation.

## Expected Directory Structure

Each isolated GUI run must live under:

```text
results/gui_runs/<run_id>/
```

The expected run-local structure is:

```text
results/gui_runs/<run_id>/
  run_manifest.json
  pipeline_stdout.log
  pipeline_stderr.log
  outputs/
    results/
      ranking_nodos.csv
  publication_package/
  review/
    run_summary.md
    run_comparison_summary.md
    run_status.json
```

Incomplete runs are allowed. Missing outputs must be reported conservatively instead of treated as evidence.

## Allowed Generated Files

The GUI-controlled runner and review workflow may generate or update files only inside the selected GUI run directory:

```text
results/gui_runs/<run_id>/
```

Allowed run-local files include:

- `run_manifest.json`
- `pipeline_stdout.log`
- `pipeline_stderr.log`
- files below `outputs/`
- files below `publication_package/`
- files below `review/`

Generated publication packages must remain inside the selected GUI run directory:

```text
results/gui_runs/<run_id>/publication_package/
```

The run-local publication package must not overwrite the base package at:

```text
results/publication_package/
```

Comparison output writes only to `review/`:

```text
results/gui_runs/<run_id>/review/
```

## Read-Only Or Untouched Areas

The validation layer must treat these locations as read-only during GUI run review:

- `results/publication_package/`
- existing base publication reports and figures
- curated input datasets outside the selected run
- `data_raw/`
- `data_user/`
- `data_processed/`
- `data_sessions/`
- `config/taxon_resolution_cache.json`

The GUI review workflow may read base publication files for comparison, but it must not modify them. Cache files such as `config/taxon_resolution_cache.json` must not be included when they only change because of timestamps, refresh counters, EOL metadata, index refresh or other cache metadata.

## Separation Of Concerns

The workflow keeps three outputs separate:

1. Execution output: pipeline files generated under `results/gui_runs/<run_id>/outputs/`.
2. Publication package: run-local manuscript/demo artifacts generated under `results/gui_runs/<run_id>/publication_package/`.
3. Review comparison: conservative summaries and comparison status generated under `results/gui_runs/<run_id>/review/`.

This separation makes it possible to inspect what the pipeline produced, what was packaged for reporting and what the GUI review layer concluded without mixing those artifacts.

## Conservative Interpretation Rules

GUI run-review language must remain conservative:

- Ranked candidates are computationally prioritized hypotheses requiring independent validation.
- Score ranking is not experimental validation.
- A high `therapeutic_priority_score` does not prove efficacy, safety or clinical usefulness.
- `therapeutic_priority_score` and `evidence_confidence_score` must remain distinct. The first ranks therapeutic-priority hypotheses; the second reports evidence support, provenance and interpretability constraints.
- `user_curated` evidence is curator-provided evidence. It is not automatically external validation and must not be presented as independent confirmation.
- Comparison against the base publication package is a workflow and artifact comparison, not proof that one candidate list is biologically superior.
- Missing, proxy, preliminary, demo-only or insufficient evidence flags must stay visible in reports.

## Publication Relevance

This validation layer is publication-relevant because it documents that GUI-generated runs are:

- reproducible enough to be rerun from a recorded manifest;
- isolated from base project outputs;
- reviewable through logs, output inventories and package summaries;
- auditable through explicit run-local publication packages;
- comparable against the base publication package without overwriting it;
- suitable as evidence for software-methods claims in a manuscript or demo.

The supported claim is that the workflow can produce isolated and reviewable computational artifacts. It does not claim that the ranked nodes are validated therapeutic targets.

## Current Limitations

This validation does not assess biological truth, clinical utility, antimicrobial efficacy, host safety or experimental reproducibility in a wet-lab setting.

The controlled demo depends on available local inputs and offline fixtures. If a future phase adds real online providers to the GUI workflow, those providers must remain optional, provenance-tracked and routed through the existing resolution architecture.

Future work should add a small controlled demo fixture that exercises run creation, package generation and review comparison end to end while preserving the same directory and write-boundary rules.
