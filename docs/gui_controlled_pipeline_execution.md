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
```

The `outputs/` directory is passed as the pipeline workspace so generated files remain isolated from the main publication package.

## Preflight

Preflight validates required inputs, run id format, mode, acquisition mode and proposed paths. It builds the safe command as an argument list and does not execute it.

## Controlled Execution

Controlled execution calls `subprocess.run(..., shell=False)` from `pipeline_runner.py` only. Execution is disabled by default through `allow_execution=False`; the GUI requires an explicit checkbox before running.

## Conservative Interpretation

Generated outputs, if any, are computationally prioritized hypotheses requiring independent validation. They do not represent experimental, pharmacological or clinical confirmation.

## Current Limitations

The controlled runner uses the existing `run_pipeline.py --workspace <isolated outputs>` entrypoint. If future pipeline behavior writes outside the workspace, that behavior must be documented in `run_manifest.json` and reviewed before enabling broader GUI execution.
