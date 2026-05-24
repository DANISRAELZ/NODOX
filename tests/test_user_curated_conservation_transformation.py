from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.user_curated_transformations import (
    STRAIN_CONSERVATION_TEMPLATE_COLUMNS,
    transform_user_curated_conservation_to_strain_conservation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _minimal_user_curated_conservation_csv() -> str:
    return (
        "organism,strain,protein_id,gene,conservation_scope,core_genome_presence,"
        "strain_coverage_score,allelic_conservation,variant_burden,source_database,"
        "evidence_status,curator_notes\n"
        "Example bacterium,minimal_validation_scope,candidate_A_protein,candidate_A,"
        "local validation panel,true,0.80,0.70,0.10,user_curated_local_note,"
        "reviewed,curated conservation note\n"
        "Example bacterium,minimal_validation_scope,candidate_B_protein,candidate_B,"
        "local validation panel,unknown,,unknown,unknown,user_curated_local_note,"
        "insufficient_evidence,missing conservation remains unresolved risk\n"
    )


def test_transform_user_curated_conservation_success_uses_template_columns(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(source, _minimal_user_curated_conservation_csv())

    result = transform_user_curated_conservation_to_strain_conservation(source)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == STRAIN_CONSERVATION_TEMPLATE_COLUMNS
    assert list(result.columns) == [
        "protein_id",
        "gene",
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
        "database",
    ]
    assert len(result) == 2


def test_transform_preserves_identity_and_traceability_metadata(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(source, _minimal_user_curated_conservation_csv())

    result = transform_user_curated_conservation_to_strain_conservation(source)
    first = result.iloc[0].to_dict()

    assert first["protein_id"] == "candidate_A_protein"
    assert first["gene"] == "candidate_A"
    assert first["core_genome_presence"] == "1"
    assert first["strain_coverage_score"] == "0.80"
    assert first["allelic_conservation"] == "0.70"
    assert first["variant_burden"] == "0.10"

    database = first["database"]
    assert "source_database=user_curated_local_note" in database
    assert "source_type=user_curated" in database
    assert "organism=Example bacterium" in database
    assert "strain=minimal_validation_scope" in database
    assert "conservation_scope=local validation panel" in database
    assert "evidence_status=reviewed" in database
    assert "curator_notes=curated conservation note" in database


def test_transform_preserves_uncertainty_without_converting_to_low_risk(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(source, _minimal_user_curated_conservation_csv())

    result = transform_user_curated_conservation_to_strain_conservation(source)
    uncertain = result.iloc[1].to_dict()

    assert uncertain["core_genome_presence"] == "unknown"
    assert uncertain["strain_coverage_score"] == ""
    assert uncertain["allelic_conservation"] == "unknown"
    assert uncertain["variant_burden"] == "unknown"
    assert "evidence_status=insufficient_evidence" in uncertain["database"]
    assert "missing conservation remains unresolved risk" in uncertain["database"]
    assert "low_risk" not in uncertain["database"].casefold()
    assert "low risk" not in uncertain["database"].casefold()


def test_transform_does_not_invent_scores_or_priority_columns(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(source, _minimal_user_curated_conservation_csv())

    result = transform_user_curated_conservation_to_strain_conservation(source)

    forbidden_columns = {
        "conservation_score",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "risk_score",
        "priority",
    }
    assert forbidden_columns.isdisjoint(result.columns)


def test_transform_missing_critical_columns_raises_clear_error(tmp_path: Path) -> None:
    source = tmp_path / "bad_conservation.csv"
    _write_csv(
        source,
        "organism,strain,protein_id,gene,core_genome_presence\n"
        "Example bacterium,minimal_validation_scope,candidate_A_protein,candidate_A,true\n",
    )

    with pytest.raises(ValueError, match="missing required columns") as excinfo:
        transform_user_curated_conservation_to_strain_conservation(source)

    error = str(excinfo.value)
    assert "conservation_scope" in error
    assert "strain_coverage_score" in error
    assert "source_database" in error
    assert "evidence_status" in error
    assert "curator_notes" in error


def test_transform_is_pure_and_does_not_touch_project_local_workspaces(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(source, _minimal_user_curated_conservation_csv())

    before_tmp_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}
    transform_user_curated_conservation_to_strain_conservation(source)
    after_tmp_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}

    assert after_tmp_files == before_tmp_files
    assert not (tmp_path / "user_curated_staging").exists()
    assert not (tmp_path / "data_sessions").exists()


def test_transform_has_no_organism_defaults_and_stays_multi_organism(tmp_path: Path) -> None:
    source = tmp_path / "conservation.csv"
    _write_csv(
        source,
        "organism,strain,protein_id,gene,conservation_scope,core_genome_presence,"
        "strain_coverage_score,allelic_conservation,variant_burden,source_database,"
        "evidence_status,curator_notes\n"
        "Another bacterium,custom_scope,custom_protein,custom_gene,custom panel,false,"
        "0.40,0.50,0.30,user_curated_custom,reviewed,custom organism note\n",
    )

    result = transform_user_curated_conservation_to_strain_conservation(source)
    database = result.iloc[0]["database"]

    assert "organism=Another bacterium" in database
    assert "strain=custom_scope" in database
    assert result.iloc[0]["core_genome_presence"] == "0"
    forbidden_defaults = ["PAO1", "H37Rv", "Corynebacterium"]
    assert not any(token in database for token in forbidden_defaults)


def test_transform_module_does_not_call_scoring_pipeline_or_online_modes() -> None:
    module_path = PROJECT_ROOT / "src" / "nodos_funcionales" / "user_curated_transformations.py"
    source_text = module_path.read_text(encoding="utf-8")

    forbidden_terms = [
        "run_pipeline",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "online",
        "data_sessions",
        "user_curated_staging",
    ]

    for term in forbidden_terms:
        assert term not in source_text
