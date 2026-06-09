from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "pseudomonas_aeruginosa_publication_demo_phase2_results.md"
SUMMARY_PATH = (
    PROJECT_ROOT
    / "examples"
    / "pseudomonas_aeruginosa_publication_demo"
    / "expected_outputs"
    / "publication_candidate_summary.csv"
)
FORBIDDEN_TERMS = [
    "clinically_valid",
    "validated_experimentally",
    "safe_target",
    "definitive_target",
    "confirmed_drug_target",
]
EXPECTED_COLUMNS = [
    "gene",
    "protein_id",
    "functional_role",
    "therapeutic_priority_score",
    "evidence_confidence_score",
    "evidence_strength",
    "evolutionary_escape_risk",
    "evolutionary_constraint",
    "resistance_association",
    "provenance",
    "interpretation",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def test_phase2_results_document_exists_and_mentions_required_context() -> None:
    assert DOC_PATH.is_file()
    text = _read_text(DOC_PATH)
    lower_text = text.lower()

    for required in [
        "Pseudomonas aeruginosa",
        "examples/pseudomonas_aeruginosa_publication_demo",
        "user_curated",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "evidence_strength",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "resistance_association",
        "provenance",
    ]:
        assert required in text

    for conservative_phrase in [
        "no es validacion clinica",
        "no es validacion experimental",
        "score alto no equivale a confianza alta",
        "evidencia insuficiente no equivale a bajo riesgo",
    ]:
        assert conservative_phrase in lower_text


def test_phase2_results_document_avoids_disallowed_claim_terms() -> None:
    lower_text = _read_text(DOC_PATH).lower()

    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in lower_text


def test_publication_candidate_summary_template_is_conservative() -> None:
    assert SUMMARY_PATH.is_file()
    columns, rows = _read_csv(SUMMARY_PATH)
    lower_table = SUMMARY_PATH.read_text(encoding="utf-8").lower()

    assert columns == EXPECTED_COLUMNS
    assert rows
    assert {row["provenance"] for row in rows} <= {"user_curated", "demo_publication_template"}
    assert "corynebacterium" not in lower_table
    assert "low_risk" not in lower_table

    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in lower_table

    for row in rows:
        if row["evidence_strength"] == "insufficient":
            assert row["evolutionary_escape_risk"] == "unresolved_risk"
            assert row["interpretation"] in {
                "requires_expert_review",
                "insufficient_evidence_unresolved_risk",
                "candidate_for_reproducible_demo_only",
            }

