from __future__ import annotations

import csv
from pathlib import Path

from src.nodos_funcionales.user_curated_validation import (
    USER_CURATED_MANIFEST_COLUMNS,
    validate_user_curated_manifest,
)


def _write_manifest(path: Path, rows: list[dict[str, str]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = columns or USER_CURATED_MANIFEST_COLUMNS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})


def _valid_row() -> dict[str, str]:
    return {
        "organism": "Example organism",
        "strain": "Example isolate",
        "dataset_id": "essentiality_user_dataset",
        "dataset_version": "v1",
        "curator_name": "Example curator",
        "curation_date": "2026-05-17",
        "source_type": "user_curated",
        "evidence_status": "reviewed",
        "evidence_kind": "local_export",
        "provenance": "local reviewed export",
        "input_file": "essentiality.csv",
        "input_schema": "data_templates/essentiality_template.csv",
        "required_for_scoring": "true",
        "notes": "minimal valid manifest row",
    }


def test_validate_user_curated_manifest_accepts_minimal_valid_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "user_curated_dataset_manifest.csv"
    _write_manifest(manifest_path, [_valid_row()])

    assert validate_user_curated_manifest(manifest_path) == []


def test_validate_user_curated_manifest_reports_missing_file(tmp_path: Path) -> None:
    errors = validate_user_curated_manifest(tmp_path / "missing_manifest.csv")

    assert errors
    assert "does not exist" in errors[0]


def test_validate_user_curated_manifest_reports_missing_columns(tmp_path: Path) -> None:
    manifest_path = tmp_path / "user_curated_dataset_manifest.csv"
    columns = [column for column in USER_CURATED_MANIFEST_COLUMNS if column != "notes"]
    _write_manifest(manifest_path, [_valid_row()], columns=columns)

    errors = validate_user_curated_manifest(manifest_path)

    assert any("columns must match expected contract exactly" in error for error in errors)


def test_validate_user_curated_manifest_requires_user_curated_source_type(tmp_path: Path) -> None:
    manifest_path = tmp_path / "user_curated_dataset_manifest.csv"
    row = _valid_row()
    row["source_type"] = "demo"
    _write_manifest(manifest_path, [row])

    errors = validate_user_curated_manifest(manifest_path)

    assert any("source_type must be user_curated" in error for error in errors)


def test_validate_user_curated_manifest_reports_empty_required_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "user_curated_dataset_manifest.csv"
    row = _valid_row()
    row["organism"] = ""
    row["dataset_id"] = " "
    row["input_file"] = ""
    _write_manifest(manifest_path, [row])

    errors = validate_user_curated_manifest(manifest_path)

    assert any("organism must not be empty" in error for error in errors)
    assert any("dataset_id must not be empty" in error for error in errors)
    assert any("input_file must not be empty" in error for error in errors)


def test_validate_user_curated_manifest_rejects_forbidden_organism_defaults(tmp_path: Path) -> None:
    manifest_path = tmp_path / "user_curated_dataset_manifest.csv"
    row = _valid_row()
    row["organism"] = "Pseudomonas aeruginosa PAO1"
    row["notes"] = "Do not use H37Rv, Corynebacterium or Mycobacterium tuberculosis as defaults."
    _write_manifest(manifest_path, [row])

    errors = validate_user_curated_manifest(manifest_path)

    assert any("Pseudomonas aeruginosa" in error for error in errors)
    assert any("PAO1" in error for error in errors)
    assert any("H37Rv" in error for error in errors)
    assert any("Corynebacterium" in error for error in errors)
    assert any("Mycobacterium tuberculosis" in error for error in errors)
