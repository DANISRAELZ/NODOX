# GUI Controlled Pipeline Execution

## Purpose

The optional Streamlit GUI can prepare and review controlled pipeline execution from a local interface. Execution is mediated by `src/nodos_funcionales/pipeline_runner.py` so the GUI does not construct arbitrary shell commands.

## What It Can Do

- Validate basic run inputs.
- Create a safe `run_id`.
- Propose an isolated output directory under `results/gui_runs/<run_id>/`.
- Run preflight / dry-run without executing the full pipeline.
- Run a controlled pipeline command only after explicit user confirmation.
- Capture `pipeline_stdout.log`, `pipeline_stderr.log` and `run_manifest.json`.
- List previous GUI runs.

## What It Does Not Do

- It does not accept free-form shell commands.
- It does not execute Snakemake directly.
- It does not modify `results/publication_package/`.
- It does not intentionally write to root `results/`, `data_processed/` or `data_sessions/`.
- It does not use internet by default.
- It does not provide experimental, pharmacological or clinical confirmation.

## Isolated Output

GUI-triggered runs use:

```text
results/gui_runs/<run_id>/
```

The run directory contains:

```text
run_manifest.json
pipeline_stdout.log
pipeline_stderr.log
outputs/
publication_package/
review/
```

The `review/` folder may contain:

```text
run_summary.md
run_comparison_summary.md
run_status.json
```

The `outputs/` directory is passed as the pipeline workspace so generated files remain isolated from the main publication package.

## Preflight

Preflight validates required inputs, run id format, mode, acquisition mode and proposed paths. It builds the safe command as an argument list and does not execute it.

## Controlled Execution

Controlled execution calls `subprocess.run(..., shell=False)` from `pipeline_runner.py` only. Execution is disabled by default through `allow_execution=False`; the GUI requires an explicit checkbox before running.

## Conservative Interpretation

Generated outputs, if any, are computationally prioritized hypotheses requiring independent validation. They do not represent experimental, pharmacological or clinical confirmation.

## Run Review

Run review logic lives in `src/nodos_funcionales/gui_run_review.py` and does not depend on Streamlit. It can:

- summarize incomplete or complete GUI runs;
- read stdout and stderr logs with truncation;
- list detected files under the isolated `outputs/` directory;
- detect a run-local `publication_package/`;
- write `review/run_summary.md`;
- compare a run-local package against the base `results/publication_package/`;
- write `review/run_comparison_summary.md` and `review/run_status.json`.

## Isolated Publication Package Generation

If the isolated workspace contains:

```text
results/gui_runs/<run_id>/outputs/results/ranking_nodos.csv
```

the GUI can call the controlled helper to generate:

```text
results/gui_runs/<run_id>/publication_package/
```

This action requires explicit confirmation in the GUI and does not write to `results/publication_package/`.

## Comparison Against Base Package

The comparison is intentionally lightweight. It checks table presence, figure presence, candidate counts, top genes, critical columns and manifest availability. It does not claim model superiority and does not perform external biological validation.

## Current Limitations

The controlled runner uses the existing `run_pipeline.py --workspace <isolated outputs>` entrypoint. If future pipeline behavior writes outside the workspace, that behavior must be documented in `run_manifest.json` and reviewed before enabling broader GUI execution.
