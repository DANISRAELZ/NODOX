from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_final_reporting_interpretation_closure.md"


def test_user_curated_final_reporting_interpretation_closure_document_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8").lower()

    for phrase in [
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient evidence",
        "evidencia insuficiente",
        "user_curated",
        "no clinical validation",
        "no validacion clinica",
        "no experimental validation",
        "no validacion experimental",
        "conservative interpretation",
        "interpretacion conservadora",
        "provenance",
        "procedencia",
        "no safe_target",
        "no clinically_valid",
        "no validated_experimentally",
    ]:
        assert phrase in text

    for source_boundary in [
        "demo",
        "proxy",
        "cache",
        "online",
        "controlled_reference",
    ]:
        assert source_boundary in text

    for non_confidence_signal in [
        "pending_review",
        "local_note",
        "curator_notes",
        "accepted_for_test",
        "include_for_structure_check",
    ]:
        assert non_confidence_signal in text
