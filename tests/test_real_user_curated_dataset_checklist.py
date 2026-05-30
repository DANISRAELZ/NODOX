from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "real_user_curated_dataset_checklist.md"


def test_real_user_curated_dataset_checklist_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "user_curated",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient_evidence",
        "low_risk",
        "pending_review",
        "local_note",
        "curator_notes",
        "include_for_structure_check",
        "accepted_for_test",
        "needs_revision",
        "excluded_from_scoring",
        "ready_for_import",
        "conditionally_ready_for_controlled_test",
        "no clinical validation",
        "no validacion clinica",
        "no experimental validation",
        "no validacion experimental",
        "no predictor clinico",
        "plataforma de priorizacion terapeutica",
    ]:
        assert phrase in text

    assert "PowerShell" in raw_text
