from __future__ import annotations

import csv
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "first_real_user_curated_pseudomonas_aeruginosa_package"
)
RAW_INPUTS_DIR = FIXTURE_DIR / "raw_inputs"
PROTECTED_PROJECT_DIRS = ("results", "data_processed", "data_sessions")
LAYER_FILENAMES = ("gene_list.csv", "manual_curation.csv", "evidence_quality.csv")
EXPECTED_COLUMNS = {
    "gene_list.csv": {
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
    "manual_curation.csv": {
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
    "evidence_quality.csv": {
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


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


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


def _transform_package_to_tmp_layers(workspace: Path) -> None:
    """Normalize CSV copies in tmp_path only; this is not full import or scoring."""
    data_user = workspace / "data_user"
    source_exports = workspace / "source_exports"
    data_user.mkdir(parents=True)
    source_exports.mkdir(parents=True)

    for filename in LAYER_FILENAMES:
        columns, rows = _read_csv(RAW_INPUTS_DIR / filename)
        _write_csv(data_user / filename, columns, rows)
        _write_csv(source_exports / filename, columns, rows)


@pytest.fixture
def transformed_workspace(tmp_path: Path) -> Path:
    assert FIXTURE_DIR.is_dir()
    before_project_outputs = _project_output_snapshot()
    workspace = tmp_path / "workspace"
    _transform_package_to_tmp_layers(workspace)
    assert _project_output_snapshot() == before_project_outputs
    return workspace


def test_pseudomonas_user_curated_package_transforms_to_tmp_data_user_layers(
    transformed_workspace: Path,
) -> None:
    for directory_name in ["data_user", "source_exports"]:
        directory = transformed_workspace / directory_name
        assert directory.is_dir()
        assert {path.name for path in directory.glob("*.csv")} == set(LAYER_FILENAMES)

    for filename, expected_columns in EXPECTED_COLUMNS.items():
        columns, rows = _read_csv(transformed_workspace / "data_user" / filename)
        assert set(columns) == expected_columns
        assert rows


def test_transformed_gene_list_preserves_pseudomonas_identity(
    transformed_workspace: Path,
) -> None:
    _, gene_rows = _read_csv(transformed_workspace / "data_user" / "gene_list.csv")
    assert {row["organism_name"] for row in gene_rows} == {"Pseudomonas aeruginosa"}
    assert {row["taxon_id"] for row in gene_rows} == {"287"}


def test_transformed_user_layers_preserve_provenance_and_states(
    transformed_workspace: Path,
) -> None:
    data_user = transformed_workspace / "data_user"
    _, gene_rows = _read_csv(data_user / "gene_list.csv")
    _, curation_rows = _read_csv(data_user / "manual_curation.csv")
    _, quality_rows = _read_csv(data_user / "evidence_quality.csv")
    combined_rows = gene_rows + curation_rows + quality_rows
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

    assert {row["evidence_source"] for row in quality_rows} == {"user_curated"}
    combined_text = " ".join(
        " ".join(row.values()) for row in combined_rows
    ).lower()
    assert "pending_review is not accepted_for_test" in combined_text
    assert "does not imply experimental validation" in combined_text
    assert "risk remains unresolved" in combined_text or "unresolved risk" in combined_text
    assert "not low_risk" in combined_text or "not low risk" in combined_text

    for forbidden_positive_source in [
        "online_lookup_used: true",
        "controlled_reference_used: true",
        "demo_data_used: true",
        "proxy_data_used: true",
        "cache_data_used: true",
    ]:
        assert forbidden_positive_source not in combined_text


def test_transformed_manual_curation_preserves_interpretation_guards(
    transformed_workspace: Path,
) -> None:
    columns, rows = _read_csv(
        transformed_workspace / "data_user" / "manual_curation.csv"
    )
    assert {
        "local_note",
        "curator_notes",
        "include_for_structure_check",
    } <= set(columns)
    combined_text = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "does not imply experimental validation" in combined_text
    assert "curator_notes alone" in combined_text
    assert "local structural note only" in combined_text
    assert "local uncertainty note" in combined_text


def test_transformed_evidence_quality_keeps_scores_separate(
    transformed_workspace: Path,
) -> None:
    columns, rows = _read_csv(
        transformed_workspace / "data_user" / "evidence_quality.csv"
    )
    assert "evidence_confidence_score" in columns
    assert "therapeutic_priority_score" not in columns
    combined_text = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "therapeutic_priority_score" in combined_text
    assert "evidence_confidence_score" in combined_text
    assert "insufficient_evidence" in combined_text
    assert "risk remains unresolved" in combined_text or "unresolved risk" in combined_text


def test_source_exports_preserve_traceable_content(
    transformed_workspace: Path,
) -> None:
    for filename, expected_columns in EXPECTED_COLUMNS.items():
        data_user_columns, data_user_rows = _read_csv(
            transformed_workspace / "data_user" / filename
        )
        export_columns, export_rows = _read_csv(
            transformed_workspace / "source_exports" / filename
        )
        assert set(data_user_columns) == expected_columns
        assert export_columns == data_user_columns
        assert len(export_rows) == len(data_user_rows)
        assert export_rows == data_user_rows
        assert {row["review_status"] for row in export_rows} == {
            row["review_status"] for row in data_user_rows
        }


def test_transform_uses_safe_negative_validation_language(
    transformed_workspace: Path,
) -> None:
    transformed_text = " ".join(
        path.read_text(encoding="utf-8")
        for path in transformed_workspace.rglob("*.csv")
    ).lower()
    normalized = transformed_text
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


def test_transform_does_not_create_scoring_outputs(
    transformed_workspace: Path,
) -> None:
    forbidden_output_names = [
        "ranking_nodos.csv",
        "report_phase2.md",
        "candidate_explanations_simple",
        "candidate_audit",
        "evidence_strength_audit",
        "layer_resolution_summary",
    ]
    workspace_files = [
        str(path.relative_to(transformed_workspace)).lower()
        for path in transformed_workspace.rglob("*")
        if path.is_file()
    ]
    for forbidden_name in forbidden_output_names:
        assert not any(forbidden_name in path for path in workspace_files)

    for directory_name in PROTECTED_PROJECT_DIRS:
        assert not (transformed_workspace / directory_name).exists()
