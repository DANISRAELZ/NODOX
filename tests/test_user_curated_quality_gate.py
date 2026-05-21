from __future__ import annotations

import csv
from pathlib import Path

from src.nodos_funcionales.user_curated_quality_gate import (
    CONDITIONALLY_READY_FOR_FUTURE_CONTROLLED_SCORING,
    NOT_READY_FOR_SCORING,
    REQUIRES_EXPERT_REVIEW,
    assess_pre_scoring_readiness,
)


MANIFEST_COLUMNS = [
    "organism",
    "strain",
    "dataset_id",
    "dataset_version",
    "curator_name",
    "curation_date",
    "source_type",
    "evidence_status",
    "evidence_kind",
    "provenance",
    "input_file",
    "input_schema",
    "required_for_scoring",
    "notes",
]


def _write_manifest(path: Path, row: dict[str, str], columns: list[str] | None = None) -> None:
    fieldnames = columns or MANIFEST_COLUMNS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fieldnames})


def _complete_row(**overrides: str) -> dict[str, str]:
    row = {
        "organism": "Example bacterium",
        "strain": "isolate-1",
        "dataset_id": "example_dataset",
        "dataset_version": "2026-05-19",
        "curator_name": "reviewer",
        "curation_date": "2026-05-19",
        "source_type": "user_curated",
        "evidence_status": "reviewed",
        "evidence_kind": "experimental",
        "provenance": "Local reviewed lab record, accession ABC123",
        "input_file": "raw_inputs/example_dataset.csv",
        "input_schema": "data_templates/gene_list_template.csv",
        "required_for_scoring": "true",
        "notes": "Reviewed for pre-scoring gate only.",
    }
    row.update(overrides)
    return row


def _snapshot_paths(project_root: Path, relative_dir: str) -> set[str]:
    path = project_root / relative_dir
    if not path.exists():
        return set()
    return {str(item.relative_to(path)) for item in path.rglob("*")}


def test_invalid_manifest_returns_not_ready_for_scoring(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(), columns=MANIFEST_COLUMNS[:-1])

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == NOT_READY_FOR_SCORING
    assert assessment["errors"]


def test_manifest_with_placeholders_returns_not_ready_for_scoring(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(dataset_id="<dataset_id>"))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == NOT_READY_FOR_SCORING
    assert any("placeholder" in error.lower() for error in assessment["errors"])


def test_manifest_with_pending_evidence_requires_expert_review(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(evidence_status="pending"))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == REQUIRES_EXPERT_REVIEW
    assert any("pending" in warning.lower() for warning in assessment["warnings"])


def test_manifest_with_weak_provenance_requires_expert_review(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(provenance="tbd"))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == REQUIRES_EXPERT_REVIEW
    assert any("provenance" in warning.lower() for warning in assessment["warnings"])


def test_manifest_with_possible_demo_mix_requires_expert_review(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(notes="Reviewed after demo separation."))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == REQUIRES_EXPERT_REVIEW
    assert any("demo/proxy/cache" in warning.lower() for warning in assessment["warnings"])


def test_incomplete_manifest_row_requires_expert_review(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(input_schema=""))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == REQUIRES_EXPERT_REVIEW
    assert any("complete manifest row" in warning.lower() for warning in assessment["warnings"])


def test_manifest_with_non_user_curated_source_is_not_ready(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row(source_type="controlled_reference"))

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == NOT_READY_FOR_SCORING
    assert any("source_type" in error for error in assessment["errors"])


def test_complete_manifest_is_conditionally_ready(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row())

    assessment = assess_pre_scoring_readiness(manifest_path)

    assert assessment["status"] == CONDITIONALLY_READY_FOR_FUTURE_CONTROLLED_SCORING
    assert assessment["errors"] == []
    assert assessment["checklist"]["source_type_confirmed"] is True
    assert assessment["checklist"]["provenance_reviewed"] is True


def test_quality_gate_does_not_create_output_files(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    before = {
        "results": _snapshot_paths(project_root, "results"),
        "data_processed": _snapshot_paths(project_root, "data_processed"),
        "data_sessions": _snapshot_paths(project_root, "data_sessions"),
    }
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, _complete_row())

    assess_pre_scoring_readiness(manifest_path)

    after = {
        "results": _snapshot_paths(project_root, "results"),
        "data_processed": _snapshot_paths(project_root, "data_processed"),
        "data_sessions": _snapshot_paths(project_root, "data_sessions"),
    }
    assert after == before


def test_quality_gate_module_does_not_import_scoring() -> None:
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "src" / "nodos_funcionales" / "user_curated_quality_gate.py"
    module_text = module_path.read_text(encoding="utf-8")

    forbidden_imports = {
        "import scoring",
        "from src.nodos_funcionales.scoring",
        "from nodos_funcionales.scoring",
    }
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in module_text
