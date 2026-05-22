from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from src.nodos_funcionales.user_curated_validation import USER_CURATED_MANIFEST_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_workspace_config(workspace: Path) -> None:
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "params.yaml").write_text("", encoding="utf-8")


def _write_virulence_export(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "locus_tag,gene_name,score,vf_flag,source\n"
        "GENERIC_001,generic_gene,0.82,1,user_curated_local_export\n",
        encoding="utf-8",
    )


def _write_essentiality_template_export_with_free_columns(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "protein_id,gene,essential,evidence,database,essentiality_score,essentiality_call\n"
        "GENERIC_ESS_001,generic_essential_gene,1,manual reviewed evidence,user_curated_local_export,0.97,high\n",
        encoding="utf-8",
    )


def _valid_manifest_row(source_type: str = "user_curated") -> dict[str, str]:
    return {
        "organism": "Generic organism",
        "strain": "Generic isolate",
        "dataset_id": "generic_virulence_dataset",
        "dataset_version": "v1",
        "curator_name": "Generic curator",
        "curation_date": "2026-05-17",
        "source_type": source_type,
        "evidence_status": "reviewed",
        "evidence_kind": "local_export",
        "provenance": "reviewed local export",
        "input_file": "virulence_export.csv",
        "input_schema": "data_templates/virulence_template.csv",
        "required_for_scoring": "true",
        "notes": "temporary test manifest",
    }


def _write_manifest(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=USER_CURATED_MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def _run_import_dataset(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "import_dataset.py"), *args],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _versioned_output_files() -> set[Path]:
    protected_dirs = [
        PROJECT_ROOT / "results",
        PROJECT_ROOT / "data_processed",
        PROJECT_ROOT / "data_sessions",
    ]
    files: set[Path] = set()
    for directory in protected_dirs:
        if directory.exists():
            files.update(path.relative_to(PROJECT_ROOT) for path in directory.rglob("*") if path.is_file())
    return files


def test_import_dataset_without_manifest_flag_keeps_previous_behavior(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_workspace_config(workspace)
    source = tmp_path / "source" / "virulence_export.csv"
    _write_virulence_export(source)

    result = _run_import_dataset(
        [
            "--workspace",
            str(workspace),
            "--dataset",
            "virulence",
            "--input",
            str(source),
        ]
    )

    assert result.returncode == 0
    assert "[OK] Dataset importado: virulence" in result.stdout
    assert (workspace / "data_raw" / "virulence.csv").exists()


def test_import_dataset_with_valid_user_curated_manifest_continues(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_workspace_config(workspace)
    source = tmp_path / "source" / "virulence_export.csv"
    manifest = tmp_path / "manifest" / "user_curated_dataset_manifest.csv"
    _write_virulence_export(source)
    _write_manifest(manifest, _valid_manifest_row())

    result = _run_import_dataset(
        [
            "--workspace",
            str(workspace),
            "--dataset",
            "virulence",
            "--input",
            str(source),
            "--validate-user-curated-manifest",
            str(manifest),
        ]
    )

    assert result.returncode == 0
    assert "Manifest user_curated valido" in result.stdout
    assert "[OK] Dataset importado: virulence" in result.stdout
    assert (workspace / "data_raw" / "virulence.csv").exists()


def test_user_curated_template_columns_reach_internal_layer_and_free_columns_stay_in_source_export(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    _write_workspace_config(workspace)
    source = tmp_path / "source" / "essentiality_template_export.csv"
    manifest = tmp_path / "manifest" / "user_curated_dataset_manifest.csv"
    _write_essentiality_template_export_with_free_columns(source)
    row = _valid_manifest_row()
    row.update(
        {
            "dataset_id": "generic_essentiality_dataset",
            "input_file": source.name,
            "input_schema": "data_templates/essentiality_template.csv",
        }
    )
    _write_manifest(manifest, row)

    result = _run_import_dataset(
        [
            "--workspace",
            str(workspace),
            "--dataset",
            "essentiality",
            "--input",
            str(source),
            "--validate-user-curated-manifest",
            str(manifest),
        ]
    )

    assert result.returncode == 0
    internal_layer = workspace / "data_raw" / "essentiality.csv"
    source_export = workspace / "data_raw" / "source_exports" / source.name
    assert internal_layer.exists()
    assert source_export.exists()

    with internal_layer.open(newline="", encoding="utf-8") as handle:
        internal_rows = list(csv.DictReader(handle))
    with source_export.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))

    assert set(internal_rows[0]) == {"protein_id", "gene", "essential", "evidence", "database"}
    assert internal_rows[0]["evidence"] == "manual reviewed evidence"
    assert internal_rows[0]["database"] == "user_curated_local_export"
    assert "essentiality_score" not in internal_rows[0]
    assert "essentiality_call" not in internal_rows[0]
    assert source_rows[0]["essentiality_score"] == "0.97"
    assert source_rows[0]["essentiality_call"] == "high"


def test_import_dataset_with_invalid_user_curated_manifest_stops_before_import(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_workspace_config(workspace)
    source = tmp_path / "source" / "virulence_export.csv"
    manifest = tmp_path / "manifest" / "user_curated_dataset_manifest.csv"
    _write_virulence_export(source)
    _write_manifest(manifest, _valid_manifest_row(source_type="cache"))

    result = _run_import_dataset(
        [
            "--workspace",
            str(workspace),
            "--dataset",
            "virulence",
            "--input",
            str(source),
            "--validate-user-curated-manifest",
            str(manifest),
        ]
    )

    assert result.returncode != 0
    assert "Manifest user_curated invalido" in result.stderr
    assert "source_type must be user_curated" in result.stderr
    assert not (workspace / "data_raw" / "virulence.csv").exists()


def test_user_curated_operational_flow_is_prevalidated_and_tmp_only(tmp_path: Path) -> None:
    before_outputs = _versioned_output_files()
    workspace = tmp_path / "workspace"
    _write_workspace_config(workspace)
    source = tmp_path / "source" / "virulence_export.csv"
    valid_manifest = tmp_path / "manifest" / "valid_user_curated_dataset_manifest.csv"
    invalid_manifest = tmp_path / "manifest" / "invalid_user_curated_dataset_manifest.csv"
    _write_virulence_export(source)
    _write_manifest(valid_manifest, _valid_manifest_row())
    _write_manifest(invalid_manifest, _valid_manifest_row(source_type="cache"))

    valid_result = _run_import_dataset(
        [
            "--workspace",
            str(workspace),
            "--dataset",
            "virulence",
            "--input",
            str(source),
            "--validate-user-curated-manifest",
            str(valid_manifest),
        ]
    )

    assert valid_result.returncode == 0
    assert "Manifest user_curated valido" in valid_result.stdout
    assert "[OK] Dataset importado: virulence" in valid_result.stdout
    assert (workspace / "data_raw" / "virulence.csv").exists()

    blocked_workspace = tmp_path / "blocked_workspace"
    _write_workspace_config(blocked_workspace)
    missing_source = tmp_path / "source" / "missing_virulence_export.csv"
    invalid_result = _run_import_dataset(
        [
            "--workspace",
            str(blocked_workspace),
            "--dataset",
            "virulence",
            "--input",
            str(missing_source),
            "--validate-user-curated-manifest",
            str(invalid_manifest),
        ]
    )

    assert invalid_result.returncode != 0
    assert "Manifest user_curated invalido" in invalid_result.stderr
    assert "source_type must be user_curated" in invalid_result.stderr
    assert "No such file" not in invalid_result.stderr
    assert not (blocked_workspace / "data_raw" / "virulence.csv").exists()
    assert _versioned_output_files() == before_outputs
