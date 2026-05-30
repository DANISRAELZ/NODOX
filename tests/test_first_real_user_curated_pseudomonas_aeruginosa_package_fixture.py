from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "first_real_user_curated_pseudomonas_aeruginosa_package"
)
RAW_INPUTS_DIR = FIXTURE_DIR / "raw_inputs"


def _read_text(relative_path: str) -> str:
    return (FIXTURE_DIR / relative_path).read_text(encoding="utf-8")


def _read_csv(relative_path: str) -> tuple[list[str], list[dict[str, str]]]:
    with (FIXTURE_DIR / relative_path).open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def test_fixture_directory_and_expected_files_exist() -> None:
    assert FIXTURE_DIR.is_dir()
    for relative_path in [
        "manifest.yaml",
        "provenance.yaml",
        "raw_inputs/gene_list.csv",
        "raw_inputs/manual_curation.csv",
        "raw_inputs/evidence_quality.csv",
        "curator_notes/notes.md",
        "README_dataset.md",
    ]:
        assert (FIXTURE_DIR / relative_path).is_file()


def test_manifest_and_provenance_keep_user_curated_sources_separate() -> None:
    manifest = _read_text("manifest.yaml")
    for phrase in [
        "Pseudomonas aeruginosa",
        'taxon_id: "287"',
        "provenance_type: user_curated",
        "not_for_clinical_use: true",
        "not_clinically_validated: true",
        "not_experimentally_validated: true",
    ]:
        assert phrase in manifest

    provenance = _read_text("provenance.yaml")
    for phrase in [
        "provenance_type: user_curated",
        "online_lookup_used: false",
        "controlled_reference_used: false",
        "demo_data_used: false",
        "proxy_data_used: false",
        "cache_data_used: false",
    ]:
        assert phrase in provenance


def test_gene_list_has_minimum_columns_and_conservative_states() -> None:
    columns, rows = _read_csv("raw_inputs/gene_list.csv")
    assert set(columns) == {
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
    }
    assert len(rows) >= 4
    assert {row["review_status"] for row in rows} >= {
        "accepted_for_test",
        "needs_revision",
        "pending_review",
        "insufficient_evidence",
    }
    assert {row["organism_name"] for row in rows} == {"Pseudomonas aeruginosa"}
    assert {row["taxon_id"] for row in rows} == {"287"}


def test_manual_curation_preserves_conservative_meaning() -> None:
    columns, rows = _read_csv("raw_inputs/manual_curation.csv")
    assert {
        "local_note",
        "curator_notes",
        "include_for_structure_check",
    } <= set(columns)
    assert {row["review_status"] for row in rows} >= {
        "accepted_for_test",
        "needs_revision",
        "pending_review",
        "insufficient_evidence",
    }
    combined = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "pending_review is not accepted_for_test" in combined
    assert "curator_notes alone" in combined
    assert "does not imply experimental validation" in combined
    assert "insufficient_evidence is unresolved risk and not low_risk" in combined


def test_evidence_quality_keeps_confidence_separate_from_priority() -> None:
    columns, rows = _read_csv("raw_inputs/evidence_quality.csv")
    assert "evidence_confidence_score" in columns
    assert "therapeutic_priority_score" not in columns
    combined = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "therapeutic_priority_score" in combined
    assert "insufficient_evidence" in combined
    assert "risk remains unresolved" in combined or "unresolved risk" in combined
    assert "not low_risk" in combined or "not low risk" in combined


def test_fixture_uses_only_safe_negative_validation_language() -> None:
    fixture_text = " ".join(
        path.read_text(encoding="utf-8")
        for path in FIXTURE_DIR.rglob("*")
        if path.is_file()
    ).lower()
    normalized = fixture_text
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
        "clinically validated",
        "experimentally validated",
        "safe target",
        "confirmed therapeutic target",
        "validated target",
        "low_risk target",
    ]:
        assert prohibited_phrase not in normalized


def test_notes_explain_structural_only_interpretation() -> None:
    notes = _read_text("curator_notes/notes.md").lower()
    for phrase in [
        "local_note` no equivale a literatura externa",
        "curator_notes` no elevan confianza por si solas",
        "include_for_structure_check` no equivale a validacion experimental",
        "insufficient_evidence` significa riesgo no resuelto, no `low_risk",
        "accepted_for_test` solo significa aceptado para prueba estructural",
    ]:
        assert phrase in notes
