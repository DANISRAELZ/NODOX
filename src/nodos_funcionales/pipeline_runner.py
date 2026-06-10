from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


CONSERVATIVE_INTERPRETATION = (
    "Generated outputs, if any, are computationally prioritized hypotheses "
    "requiring independent validation. They do not represent experimental, "
    "pharmacological or clinical confirmation."
)
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_MODES = {"default", "legacy", "phase2", "compare", "phase3"}
SAFE_ACQUISITION_MODES = {"manual", "semi_auto", "auto"}


def make_run_id(prefix: str = "gui_run") -> str:
    safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", prefix).strip("_") or "gui_run"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_prefix}_{stamp}_{uuid4().hex[:8]}"


def get_default_gui_runs_dir(base_results_dir: Path | str = "results") -> Path:
    return Path(base_results_dir) / "gui_runs"


def create_gui_run_dir(run_id: str, base_results_dir: Path | str = "results") -> Path:
    _validate_run_id(run_id)
    run_dir = get_default_gui_runs_dir(base_results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "outputs").mkdir()
    return run_dir


def validate_pipeline_inputs(
    organism: str,
    strain: str | None = None,
    mode: str = "compare",
    acquisition_mode: str = "semi_auto",
    run_id: str | None = None,
    base_results_dir: Path | str = "results",
) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    resolved_paths: dict[str, str] = {}
    organism_text = str(organism or "").strip()
    if not organism_text:
        errors.append("organism is required.")
    if mode not in SAFE_MODES:
        errors.append(f"Unsupported pipeline mode: {mode}")
    if acquisition_mode not in SAFE_ACQUISITION_MODES:
        errors.append(f"Unsupported acquisition mode: {acquisition_mode}")
    if run_id is not None:
        try:
            _validate_run_id(run_id)
        except ValueError as exc:
            errors.append(str(exc))

    runs_dir = get_default_gui_runs_dir(base_results_dir)
    resolved_paths["gui_runs_dir"] = str(runs_dir)
    if run_id:
        run_dir = runs_dir / run_id
        resolved_paths["run_dir"] = str(run_dir)
        resolved_paths["workspace"] = str(run_dir / "outputs")
        if run_dir.exists():
            warnings.append(f"Run directory already exists and will not be overwritten: {run_dir}")

    if strain is None or not str(strain).strip():
        warnings.append("strain is not set; pipeline will run with organism-level context if allowed.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "resolved_paths": resolved_paths,
    }


def build_pipeline_command(
    organism: str,
    run_dir: Path | str,
    python_executable: str | None = None,
    strain: str | None = None,
    mode: str = "compare",
    acquisition_mode: str = "semi_auto",
    allow_demo_data: bool = False,
    offline_only: bool = True,
    dry_run: bool = False,
) -> list[str]:
    validation = validate_pipeline_inputs(
        organism=organism,
        strain=strain,
        mode=mode,
        acquisition_mode=acquisition_mode,
        run_id=Path(run_dir).name,
        base_results_dir=Path(run_dir).parents[1] if len(Path(run_dir).parents) > 1 else "results",
    )
    if validation["errors"]:
        raise ValueError("; ".join(str(error) for error in validation["errors"]))

    command = [
        python_executable or sys.executable,
        "run_pipeline.py",
        "--organism",
        str(organism).strip(),
        "--workspace",
        str(Path(run_dir) / "outputs"),
        "--mode",
        mode,
        "--acquisition-mode",
        acquisition_mode,
        "--no-write-taxon-cache",
    ]
    if strain and str(strain).strip():
        command.extend(["--strain", str(strain).strip()])
    if allow_demo_data:
        command.append("--allow-demo-data")
    if offline_only:
        command.append("--offline-only")
    if dry_run:
        command.append("--dry-run")
    return command


def run_pipeline_preflight(
    organism: str,
    strain: str | None = None,
    mode: str = "compare",
    acquisition_mode: str = "semi_auto",
    run_id: str | None = None,
    base_results_dir: Path | str = "results",
    allow_demo_data: bool = False,
) -> dict[str, object]:
    resolved_run_id = run_id or make_run_id()
    validation = validate_pipeline_inputs(
        organism=organism,
        strain=strain,
        mode=mode,
        acquisition_mode=acquisition_mode,
        run_id=resolved_run_id,
        base_results_dir=base_results_dir,
    )
    run_dir = get_default_gui_runs_dir(base_results_dir) / resolved_run_id
    command: list[str] = []
    if validation["ok"]:
        command = build_pipeline_command(
            organism=organism,
            strain=strain,
            mode=mode,
            acquisition_mode=acquisition_mode,
            run_dir=run_dir,
            allow_demo_data=allow_demo_data,
            dry_run=True,
        )
    return {
        "status": "not_started" if validation["ok"] else "preflight_failed",
        "run_id": resolved_run_id,
        "run_dir": str(run_dir),
        "ok": validation["ok"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "command": command,
        "will_execute": False,
        "conservative_interpretation": CONSERVATIVE_INTERPRETATION,
    }


def run_pipeline_controlled(
    organism: str,
    strain: str | None = None,
    mode: str = "compare",
    acquisition_mode: str = "semi_auto",
    run_id: str | None = None,
    base_results_dir: Path | str = "results",
    allow_demo_data: bool = False,
    allow_execution: bool = False,
    timeout_seconds: int = 900,
) -> dict[str, object]:
    preflight = run_pipeline_preflight(
        organism=organism,
        strain=strain,
        mode=mode,
        acquisition_mode=acquisition_mode,
        run_id=run_id,
        base_results_dir=base_results_dir,
        allow_demo_data=allow_demo_data,
    )
    if not preflight["ok"]:
        return _finalize_without_process(preflight, "preflight_failed")
    if not allow_execution:
        return _finalize_without_process(preflight, "not_started")

    run_dir = create_gui_run_dir(str(preflight["run_id"]), base_results_dir)
    command = build_pipeline_command(
        organism=organism,
        strain=strain,
        mode=mode,
        acquisition_mode=acquisition_mode,
        run_dir=run_dir,
        allow_demo_data=allow_demo_data,
        dry_run=False,
    )
    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    stdout_path = run_dir / "pipeline_stdout.log"
    stderr_path = run_dir / "pipeline_stderr.log"
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    status = "completed" if completed.returncode == 0 else "failed"
    manifest = write_run_manifest(
        run_dir=run_dir,
        run_id=str(preflight["run_id"]),
        command=command,
        input_paths={"organism": organism, "strain": strain or ""},
        output_dir=run_dir / "outputs",
        status=status,
        return_code=completed.returncode,
        warnings=list(preflight["warnings"]),
        errors=[],
    )
    return {
        "status": status,
        "run_id": preflight["run_id"],
        "run_dir": str(run_dir),
        "return_code": completed.returncode,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "manifest": manifest,
    }


def write_run_manifest(
    run_dir: Path | str,
    run_id: str,
    command: list[str],
    input_paths: dict[str, object],
    output_dir: Path | str,
    status: str,
    return_code: int | None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, object]:
    run_path = Path(run_dir)
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "input_paths": input_paths,
        "output_dir": str(output_dir),
        "status": status,
        "return_code": return_code,
        "conservative_interpretation": CONSERVATIVE_INTERPRETATION,
        "warnings": warnings or [],
        "errors": errors or [],
    }
    run_path.mkdir(parents=True, exist_ok=True)
    (run_path / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def list_gui_runs(base_results_dir: Path | str = "results") -> list[dict[str, object]]:
    runs_dir = get_default_gui_runs_dir(base_results_dir)
    if not runs_dir.is_dir():
        return []
    rows = []
    for run_dir in sorted((path for path in runs_dir.iterdir() if path.is_dir()), key=lambda item: item.name, reverse=True):
        manifest, error = read_gui_run_manifest(run_dir)
        rows.append(
            {
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "manifest_exists": error is None,
                "status": manifest.get("status", "not_reported") if manifest else "not_reported",
            }
        )
    return rows


def read_gui_run_manifest(run_dir: Path | str) -> tuple[dict[str, object], str | None]:
    manifest_path = Path(run_dir) / "run_manifest.json"
    if not manifest_path.exists():
        return {}, f"Missing run manifest: {manifest_path}"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f"Could not read run manifest {manifest_path}: {exc}"


def _finalize_without_process(preflight: dict[str, object], status: str) -> dict[str, object]:
    run_dir = Path(str(preflight["run_dir"]))
    manifest = write_run_manifest(
        run_dir=run_dir,
        run_id=str(preflight["run_id"]),
        command=list(preflight.get("command", [])),
        input_paths={"preflight_only": True},
        output_dir=run_dir / "outputs",
        status=status,
        return_code=None,
        warnings=list(preflight.get("warnings", [])),
        errors=list(preflight.get("errors", [])),
    )
    return {
        **preflight,
        "status": status,
        "manifest": manifest,
    }


def _validate_run_id(run_id: str) -> None:
    if not run_id or not SAFE_RUN_ID_RE.match(run_id):
        raise ValueError("run_id must contain only letters, numbers, underscore or hyphen.")
