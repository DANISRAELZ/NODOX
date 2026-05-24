from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.user_curated_transformations import (
    EVIDENCE_QUALITY_TEMPLATE_COLUMNS,
    transform_user_curated_manual_curation_to_evidence_quality,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _minimal_manual_curation_csv() -> str:
    return (
        "organism,strain,protein_id,gene,curator_name,curation_date,"
        "curation_decision,evidence_summary,evidence_status,source_database,"
        "reference_or_note,curator_notes\n"
        "Example bacterium,minimal_validation_scope,candidate_A_protein,candidate_A,"
        "Nodos local curator,2026-05-24,include_for_structure_check,"
        "Manual local validation note for structure only,pending_review,"
        "user_curated_local_note,local validation note,"
        "Curator notes preserved without clinical interpretation\n"
    )


def test_transform_manual_curation_success_uses_evidence_quality_template_columns(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == EVIDENCE_QUALITY_TEMPLATE_COLUMNS
    assert list(result.columns) == [
        "protein_id",
        "gene",
        "evidence_quality_score",
        "confidence_ceiling",
        "evidence_source_type",
        "evidence_notes",
        "audit_flags",
        "phase3_notes",
        "database",
    ]
    assert len(result) == 1


def test_transform_preserves_identity_curator_and_source_traceability(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    row = result.iloc[0].to_dict()

    assert row["protein_id"] == "candidate_A_protein"
    assert row["gene"] == "candidate_A"
    assert row["evidence_source_type"] == "user_curated_manual_curation"
    assert "organism=Example bacterium" in row["database"]
    assert "strain=minimal_validation_scope" in row["database"]
    assert "source_database=user_curated_local_note" in row["database"]
    assert "source_type=user_curated" in row["database"]
    assert "curator_name=Nodos local curator" in row["database"]
    assert "curation_date=2026-05-24" in row["database"]


def test_transform_preserves_manual_evidence_fields_as_explanation_not_score(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    row = result.iloc[0].to_dict()

    assert "evidence_summary=Manual local validation note for structure only" in row["evidence_notes"]
    assert "evidence_status=pending_review" in row["evidence_notes"]
    assert "curation_decision=include_for_structure_check" in row["evidence_notes"]
    assert "reference_or_note=local validation note" in row["evidence_notes"]
    assert "curator_notes=Curator notes preserved without clinical interpretation" in row["evidence_notes"]
    assert row["evidence_quality_score"] == "0.20"
    assert row["confidence_ceiling"] == "0.20"


def test_pending_review_does_not_become_high_confidence(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    row = result.iloc[0].to_dict()

    assert float(row["evidence_quality_score"]) < 0.5
    assert float(row["confidence_ceiling"]) < 0.5
    assert "limited_confidence" in row["audit_flags"]


def test_include_for_structure_check_is_not_biological_validation(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    row = result.iloc[0].to_dict()

    assert "not_experimental_validation" in row["audit_flags"]
    assert "no_clinical_recommendation" in row["phase3_notes"]
    assert "biological_validation" not in row["audit_flags"]


def test_local_note_does_not_become_doi_or_verified_literature(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    row = result.iloc[0].to_dict()

    assert "local_note_not_verified_literature" in row["audit_flags"]
    assert "doi" not in row["evidence_notes"].casefold()
    assert "verified_literature" not in row["evidence_notes"].casefold()


def test_transform_does_not_generate_priority_ranking_or_clinical_recommendation(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    result = transform_user_curated_manual_curation_to_evidence_quality(source)

    forbidden_columns = {
        "therapeutic_priority_score",
        "ranking",
        "clinical_recommendation",
        "recommendation",
    }
    assert forbidden_columns.isdisjoint(result.columns)


def test_transform_missing_critical_columns_raises_clear_error(tmp_path: Path) -> None:
    source = tmp_path / "bad_manual_curation.csv"
    _write_csv(
        source,
        "organism,strain,protein_id,gene,evidence_status\n"
        "Example bacterium,minimal_validation_scope,candidate_A_protein,candidate_A,pending_review\n",
    )

    with pytest.raises(ValueError, match="missing required columns") as excinfo:
        transform_user_curated_manual_curation_to_evidence_quality(source)

    error = str(excinfo.value)
    assert "curator_name" in error
    assert "curation_date" in error
    assert "curation_decision" in error
    assert "evidence_summary" in error
    assert "source_database" in error
    assert "reference_or_note" in error
    assert "curator_notes" in error


def test_transform_has_no_forbidden_organism_defaults_and_stays_multi_organism(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(
        source,
        "organism,strain,protein_id,gene,curator_name,curation_date,"
        "curation_decision,evidence_summary,evidence_status,source_database,"
        "reference_or_note,curator_notes\n"
        "Another bacterium,custom_scope,custom_protein,custom_gene,Custom curator,"
        "2026-05-24,manual_review,Custom summary,reviewed,user_curated_custom,"
        "custom reference pending,custom notes\n",
    )

    result = transform_user_curated_manual_curation_to_evidence_quality(source)
    database = result.iloc[0]["database"]

    assert "organism=Another bacterium" in database
    assert "strain=custom_scope" in database
    assert result.iloc[0]["evidence_quality_score"] == "0.40"
    assert not any(token in database for token in ["PAO1", "H37Rv", "Corynebacterium"])


def test_transform_is_pure_and_does_not_touch_project_local_workspaces(tmp_path: Path) -> None:
    source = tmp_path / "manual_curation.csv"
    _write_csv(source, _minimal_manual_curation_csv())

    before_tmp_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}
    transform_user_curated_manual_curation_to_evidence_quality(source)
    after_tmp_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}

    assert after_tmp_files == before_tmp_files
    assert not (tmp_path / "user_curated_staging").exists()
    assert not (tmp_path / "data_sessions").exists()


def test_transform_module_does_not_call_pipeline_scoring_or_online_modes() -> None:
    module_path = PROJECT_ROOT / "src" / "nodos_funcionales" / "user_curated_transformations.py"
    source_text = module_path.read_text(encoding="utf-8")

    for term in [
        "run_pipeline",
        "online",
        "data_sessions",
        "user_curated_staging",
    ]:
        assert term not in source_text
