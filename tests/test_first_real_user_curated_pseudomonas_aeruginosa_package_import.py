from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "first_real_user_curated_pseudomonas_aeruginosa_package"
)
PACKAGE_NAME = "first_real_user_curated_pseudomonas_aeruginosa_package"
PROTECTED_PROJECT_DIRS = ("results", "data_processed", "data_sessions")
EXPECTED_PACKAGE_FILES = {
    "manifest.yaml",
    "provenance.yaml",
    "raw_inputs/gene_list.csv",
    "raw_inputs/manual_curation.csv",
    "raw_inputs/evidence_quality.csv",
    "curator_notes/notes.md",
    "README_dataset.md",
}


def _read_text(package_dir: Path, relative_path: str) -> str:
    return (package_dir / relative_path).read_text(encoding="utf-8")


def _read_csv(
    package_dir: Path, relative_path: str
) -> tuple[list[str], list[dict[str, str]]]:
    with (package_dir / relative_path).open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _project_output_snapshot() -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for directory_name in PROTECTED_PROJECT_DIRS:
        directory = PROJECT_ROOT / directory_name
        if directory.exists():
            for path in directory.rglob("*"):
                if path.is_file():
                    stat = path.stat()
                    snapshot[str(path.relative_to(PROJECT_ROOT))] = (
                        stat.st_size,
                        stat.st_mtime_ns,
                    )
    return snapshot


@pytest.fixture
def staged_package(tmp_path: Path) -> Path:
    """Stage the package in tmp_path only; this does not run a full import or scoring."""
    assert FIXTURE_DIR.is_dir()
    before_project_outputs = _project_output_snapshot()
    workspace = tmp_path / "workspace"
    package_dir = workspace / "incoming" / PACKAGE_NAME
    shutil.copytree(FIXTURE_DIR, package_dir)
    (workspace / "data_user").mkdir()
    (workspace / "source_exports").mkdir()
    assert _project_output_snapshot() == before_project_outputs
    return package_dir


def test_pseudomonas_user_curated_package_can_be_staged_in_tmp_workspace(
    staged_package: Path,
) -> None:
    copied_files = {
        str(path.relative_to(staged_package)).replace("\\", "/")
        for path in staged_package.rglob("*")
        if path.is_file()
    }
    assert copied_files == EXPECTED_PACKAGE_FILES

    manifest = _read_text(staged_package, "manifest.yaml")
    for phrase in [
        "Pseudomonas aeruginosa",
        'taxon_id: "287"',
        "provenance_type: user_curated",
        "not_for_clinical_use: true",
        "not_clinically_validated: true",
        "not_experimentally_validated: true",
        "structural package validation only",
    ]:
        assert phrase in manifest


def test_staged_package_preserves_user_curated_provenance(staged_package: Path) -> None:
    provenance = _read_text(staged_package, "provenance.yaml")
    for phrase in [
        "provenance_type: user_curated",
        "online_lookup_used: false",
        "controlled_reference_used: false",
        "demo_data_used: false",
        "proxy_data_used: false",
        "cache_data_used: false",
        "review_status: pending_review",
    ]:
        assert phrase in provenance

    package_text = " ".join(
        path.read_text(encoding="utf-8")
        for path in staged_package.rglob("*")
        if path.is_file()
    ).lower()
    for forbidden_positive_source in [
        "online_lookup_used: true",
        "controlled_reference_used: true",
        "demo_data_used: true",
        "proxy_data_used: true",
        "cache_data_used: true",
    ]:
        assert forbidden_positive_source not in package_text


def test_staged_package_csv_files_have_expected_columns(staged_package: Path) -> None:
    expected_columns = {
        "raw_inputs/gene_list.csv": {
            "gene",
            "protein_id",
            "locus_tag",
            "organism_name",
            "taxon_id",
            "product",
            "candidate_label",
            "review_status",
            "curator",
            "curator_notes",
        },
        "raw_inputs/manual_curation.csv": {
            "gene",
            "protein_id",
            "curation_decision",
            "curation_summary",
            "curator",
            "curation_date",
            "review_status",
            "local_note",
            "curator_notes",
            "include_for_structure_check",
        },
        "raw_inputs/evidence_quality.csv": {
            "gene",
            "protein_id",
            "evidence_strength",
            "evidence_quality",
            "evidence_confidence_score",
            "evidence_source",
            "review_status",
            "limitations",
            "curator_notes",
        },
    }
    for relative_path, expected in expected_columns.items():
        columns, rows = _read_csv(staged_package, relative_path)
        assert set(columns) == expected
        assert rows


def test_staged_package_preserves_conservative_review_states(
    staged_package: Path,
) -> None:
    _, gene_rows = _read_csv(staged_package, "raw_inputs/gene_list.csv")
    _, curation_rows = _read_csv(staged_package, "raw_inputs/manual_curation.csv")
    combined_rows = gene_rows + curation_rows
    statuses = {row["review_status"] for row in combined_rows}
    assert statuses >= {
        "accepted_for_test",
        "needs_revision",
        "pending_review",
        "insufficient_evidence",
    }
    if "excluded_from_scoring" in statuses:
        assert any(
            row["review_status"] == "excluded_from_scoring" for row in combined_rows
        )

    combined_text = " ".join(
        " ".join(row.values()) for row in combined_rows
    ).lower()
    assert "risk remains unresolved" in combined_text or "unresolved risk" in combined_text
    assert "pending_review is not accepted_for_test" in combined_text
    assert "included only to verify package structure" in combined_text
    assert "does not imply experimental validation" in combined_text


def test_staged_evidence_quality_keeps_scores_separate(staged_package: Path) -> None:
    columns, rows = _read_csv(staged_package, "raw_inputs/evidence_quality.csv")
    assert "evidence_confidence_score" in columns
    assert "therapeutic_priority_score" not in columns
    assert {row["evidence_source"] for row in rows} == {"user_curated"}

    combined_text = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "therapeutic_priority_score" in combined_text
    assert "evidence_confidence_score" in combined_text
    assert "insufficient_evidence" in combined_text
    assert "risk remains unresolved" in combined_text or "unresolved risk" in combined_text
    assert "not low_risk" in combined_text or "not low risk" in combined_text


def test_staged_package_uses_safe_negative_validation_language(
    staged_package: Path,
) -> None:
    package_text = " ".join(
        path.read_text(encoding="utf-8")
        for path in staged_package.rglob("*")
        if path.is_file()
    ).lower()
    normalized = package_text
    for allowed_negative_phrase in [
        "not clinically validated",
        "not experimentally validated",
        "not a validated target",
        "not low_risk",
        "not low risk",
        "do not present as validated target",
    ]:
        normalized = normalized.replace(allowed_negative_phrase, "")

    for prohibited_phrase in [
        "clinically validated target",
        "experimentally validated target",
        "safe target",
        "confirmed therapeutic target",
        "low_risk target",
    ]:
        assert prohibited_phrase not in normalized


def test_staged_notes_and_readme_explain_structural_only_scope(
    staged_package: Path,
) -> None:
    notes = _read_text(staged_package, "curator_notes/notes.md").lower()
    for phrase in [
        "no uso clinico",
        "no predictor clinico",
        "no validacion clinica",
        "no validacion experimental",
        "local_note",
        "curator_notes",
        "include_for_structure_check",
        "insufficient_evidence",
        "low_risk",
        "accepted_for_test",
    ]:
        assert phrase in notes

    readme = _read_text(staged_package, "README_dataset.md").lower()
    for phrase in [
        "pseudomonas aeruginosa",
        "user_curated",
        "no uso clinico",
        "no validacion clinica",
        "no validacion experimental",
        "no ejecuta scoring",
        "online",
        "demo",
        "proxy",
        "cache",
        "controlled_reference",
    ]:
        assert phrase in readme


def test_staged_package_does_not_create_scoring_outputs(staged_package: Path) -> None:
    workspace = staged_package.parents[1]
    forbidden_output_names = [
        "ranking_nodos.csv",
        "report_phase2.md",
        "candidate_explanations_simple",
        "candidate_audit",
        "evidence_strength_audit",
        "layer_resolution_summary",
    ]
    workspace_files = [
        str(path.relative_to(workspace)).lower()
        for path in workspace.rglob("*")
        if path.is_file()
    ]
    for forbidden_name in forbidden_output_names:
        assert not any(forbidden_name in path for path in workspace_files)

    for directory_name in PROTECTED_PROJECT_DIRS:
        assert not (workspace / directory_name).exists()
