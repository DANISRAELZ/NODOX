from __future__ import annotations

import csv
from pathlib import Path

from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "tests" / "fixtures" / "real_user_curated_minimal_validation_01"
RAW_INPUTS = DATASET_DIR / "raw_inputs"
DATA_USER = DATASET_DIR / "data_user"
MANIFEST_PATH = DATASET_DIR / "manifest.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_real_user_curated_minimal_dataset_exists_and_manifest_is_valid() -> None:
    assert DATASET_DIR.exists()
    assert MANIFEST_PATH.exists()
    assert validate_user_curated_manifest(MANIFEST_PATH) == []


def test_real_user_curated_minimal_dataset_has_required_layers_and_columns() -> None:
    expected_columns = {
        "essentiality.csv": {"protein_id", "gene", "essential", "evidence", "database"},
        "virulence.csv": {"protein_id", "gene", "virulence_score", "virulence_factor", "database"},
        "human_homologs.csv": {
            "protein_id",
            "gene",
            "human_homolog",
            "evalue",
            "source_database",
            "evidence_source_type",
            "curator_notes",
            "orthology_confidence_score",
            "orthology_evidence_note",
            "database",
        },
        "localization.csv": {"protein_id", "gene", "localization", "database"},
        "manual_curation.csv": {
            "organism",
            "strain",
            "protein_id",
            "gene",
            "curator_name",
            "curation_date",
            "curation_decision",
            "evidence_summary",
            "evidence_status",
            "source_database",
            "reference_or_note",
            "curator_notes",
        },
        "evidence_quality.csv": {
            "protein_id",
            "gene",
            "evidence_quality_score",
            "confidence_ceiling",
            "evidence_source_type",
            "evidence_notes",
            "audit_flags",
            "phase3_notes",
            "database",
        },
    }

    for filename, columns in expected_columns.items():
        path = RAW_INPUTS / filename
        assert path.exists()
        rows = _rows(path)
        assert rows
        assert columns.issubset(rows[0].keys())


def test_manifest_preserves_user_curated_minimal_validation_separation() -> None:
    rows = _rows(MANIFEST_PATH)
    assert rows
    forbidden_source_types = {"demo", "proxy", "cache", "online", "controlled_reference"}

    for row in rows:
        assert row["organism"] == "Validation bacterium alpha"
        assert row["strain"] == "minimal_validation_scope_01"
        assert row["source_type"] == "user_curated"
        assert row["source_type"] not in forbidden_source_types
        assert "minimal" in row["dataset_version"]
        assert "external_verified" not in row["source_type"]
        assert row["input_file"]
        assert row["input_schema"].startswith("data_templates/")


def test_local_notes_and_pending_review_do_not_become_strong_evidence() -> None:
    manual_rows = _rows(RAW_INPUTS / "manual_curation.csv")
    quality_rows = _rows(RAW_INPUTS / "evidence_quality.csv")

    pending_manual = next(row for row in manual_rows if row["evidence_status"] == "pending_review")
    pending_quality = next(row for row in quality_rows if row["protein_id"] == pending_manual["protein_id"])

    assert pending_manual["curation_decision"] == "include_for_structure_check"
    assert "local_note" in pending_manual["reference_or_note"]
    assert "not strong evidence" in pending_manual["curator_notes"]
    assert float(pending_quality["evidence_quality_score"]) < 0.5
    assert float(pending_quality["confidence_ceiling"]) < 0.5
    assert "limited_confidence" in pending_quality["audit_flags"]
    assert "not_experimental_validation" in pending_quality["audit_flags"]


def test_evidence_quality_is_interpretive_not_experimental_or_clinical_validation() -> None:
    quality_text = (RAW_INPUTS / "evidence_quality.csv").read_text(encoding="utf-8").lower()
    notes_text = (DATASET_DIR / "notes" / "interpretation_limits.md").read_text(encoding="utf-8").lower()

    assert "not experimental validation" in quality_text
    assert "not clinical recommendation" in quality_text
    assert "evidence_quality" in notes_text
    assert "not automatic experimental validation" in notes_text
    assert "insufficient evidence does not imply low risk" in notes_text
    assert "not a clinical or experimental predictor" in notes_text


def test_insufficient_evidence_is_preserved_as_uncertain_not_low_risk() -> None:
    human_rows = _rows(RAW_INPUTS / "human_homologs.csv")
    uncertain = next(row for row in human_rows if row["protein_id"] == "VBALPHA_0002")

    assert "insufficient_evidence" in uncertain["database"]
    assert "not low risk" in uncertain["orthology_evidence_note"]
    assert "pending_review does not imply low host risk" in uncertain["curator_notes"]


def test_fixture_includes_minimal_user_layers_without_results_or_processed_outputs() -> None:
    imported_layers = {
        "essentiality.csv",
        "virulence.csv",
        "human_homologs.csv",
        "localization.csv",
        "evidence_quality.csv",
    }

    for filename in imported_layers:
        assert (DATA_USER / filename).exists()

    assert not (DATASET_DIR / "results").exists()
    assert not (DATASET_DIR / "data_processed").exists()


def test_imported_user_layers_preserve_interpretive_quality_and_traceability() -> None:
    quality_rows = _rows(DATA_USER / "evidence_quality.csv")
    homolog_rows = _rows(DATA_USER / "human_homologs.csv")

    pending_quality = next(row for row in quality_rows if row["protein_id"] == "VBALPHA_0002")
    pending_homolog = next(row for row in homolog_rows if row["protein_id"] == "VBALPHA_0002")

    assert pending_quality["evidence_source_type"] == "user_curated_manual_curation"
    assert float(pending_quality["evidence_quality_score"]) == 0.2
    assert float(pending_quality["confidence_ceiling"]) == 0.2
    assert "limited_confidence" in pending_quality["audit_flags"]
    assert "insufficient_evidence is not low risk" in pending_quality["phase3_notes"]
    assert pending_homolog["source_database"] == "user_curated_minimal_validation"
    assert pending_homolog["evidence_source_type"] == "user_curated_manual_review"
    assert "pending_review does not imply low host risk" in pending_homolog["curator_notes"]
