from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_minimal_functional_validation_flow_closure.md"


def test_user_curated_minimal_functional_validation_flow_closure_document_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "user_curated",
        "minimal functional validation flow",
        "portable",
        "temporary workspace",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient evidence",
        "conservative interpretation",
        "provenance",
        "no clinical validation",
        "no experimental validation",
        "safe_target",
        "clinically_valid",
        "validated_clinically",
        "validated_experimentally",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
    ]:
        assert phrase in text

    for organism_token in [
        "PAO1",
        "H37Rv",
        "Corynebacterium",
    ]:
        assert organism_token in raw_text

    for operational_signal in [
        "pending_review",
        "local_note",
        "curator_notes",
    ]:
        assert operational_signal in text
