from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from src.nodos_funcionales.pipeline_runner import (
    build_pipeline_command,
    create_gui_run_dir,
    get_default_gui_runs_dir,
    list_gui_runs,
    make_run_id,
    read_gui_run_manifest,
    run_pipeline_controlled,
    run_pipeline_preflight,
    validate_pipeline_inputs,
    write_run_manifest,
)


def test_make_run_id_generates_safe_ids() -> None:
    run_id = make_run_id("gui run")

    assert run_id.startswith("gui_run_")
    assert all(char.isalnum() or char in {"_", "-"} for char in run_id)


def test_create_gui_run_dir_does_not_overwrite(tmp_path: Path) -> None:
    run_dir = create_gui_run_dir("gui_run_test", tmp_path)

    assert run_dir == tmp_path / "gui_runs" / "gui_run_test"
    assert (run_dir / "outputs").is_dir()
    with pytest.raises(FileExistsError):
        create_gui_run_dir("gui_run_test", tmp_path)


def test_validate_pipeline_inputs_reports_missing_organism(tmp_path: Path) -> None:
    result = validate_pipeline_inputs("", base_results_dir=tmp_path)

    assert result["ok"] is False
    assert "organism is required." in result["errors"]
    assert "gui_runs_dir" in result["resolved_paths"]


def test_build_pipeline_command_returns_safe_argument_list(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_runs" / "gui_run_safe"
    command = build_pipeline_command(
        organism="Example bacterium",
        strain="isolate-1",
        run_dir=run_dir,
        python_executable="python",
        dry_run=True,
    )

    assert isinstance(command, list)
    assert command[0] == "python"
    assert "run_pipeline.py" in command
    assert "--workspace" in command
    assert str(run_dir / "outputs") in command
    assert "--dry-run" in command
    assert all("|" not in part and "&&" not in part for part in command)


def test_build_pipeline_command_rejects_invalid_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_pipeline_command("Example bacterium", tmp_path / "gui_runs" / "gui_run_x", mode="compare; rm")


def test_run_pipeline_preflight_does_not_execute(tmp_path: Path) -> None:
    result = run_pipeline_preflight(
        organism="Example bacterium",
        run_id="gui_run_preflight",
        base_results_dir=tmp_path,
    )

    assert result["status"] == "not_started"
    assert result["will_execute"] is False
    assert "--dry-run" in result["command"]
    assert not (tmp_path / "gui_runs" / "gui_run_preflight").exists()


def test_run_pipeline_controlled_is_protected_by_default(tmp_path: Path) -> None:
    result = run_pipeline_controlled(
        organism="Example bacterium",
        run_id="gui_run_no_exec",
        base_results_dir=tmp_path,
    )

    run_dir = tmp_path / "gui_runs" / "gui_run_no_exec"
    assert result["status"] == "not_started"
    assert (run_dir / "run_manifest.json").is_file()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert "computationally prioritized hypotheses requiring independent validation" in manifest["conservative_interpretation"]
    assert "outputs_dir" in manifest
    assert "publication_package_dir" in manifest
    assert manifest["execution_mode"] == "controlled_gui"
    assert manifest["allow_execution"] is False
    assert manifest["package_generated"] is False
    assert manifest["comparison_generated"] is False
    assert not (tmp_path / "publication_package").exists()


def test_run_pipeline_controlled_uses_shell_false_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {}

    def fake_run(command, cwd, shell, capture_output, text, timeout, check):  # noqa: ANN001
        calls["command"] = command
        calls["shell"] = shell
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_pipeline_controlled(
        organism="Example bacterium",
        run_id="gui_run_exec",
        base_results_dir=tmp_path,
        allow_execution=True,
    )

    assert result["status"] == "completed"
    assert calls["shell"] is False
    assert isinstance(calls["command"], list)
    assert (tmp_path / "gui_runs" / "gui_run_exec" / "pipeline_stdout.log").read_text(encoding="utf-8") == "ok"
    manifest = json.loads((tmp_path / "gui_runs" / "gui_run_exec" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["allow_execution"] is True
    assert manifest["completed_at"] is not None


def test_list_and_read_gui_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_runs" / "gui_run_list"
    write_run_manifest(
        run_dir=run_dir,
        run_id="gui_run_list",
        command=["python", "run_pipeline.py"],
        input_paths={"organism": "Example bacterium"},
        output_dir=run_dir / "outputs",
        status="completed",
        return_code=0,
    )

    runs = list_gui_runs(tmp_path)
    manifest, error = read_gui_run_manifest(run_dir)

    assert runs[0]["run_id"] == "gui_run_list"
    assert runs[0]["status"] == "completed"
    assert error is None
    assert manifest["status"] == "completed"
    assert manifest["outputs_dir"].endswith("outputs")
    assert manifest["publication_package_dir"].endswith("publication_package")
