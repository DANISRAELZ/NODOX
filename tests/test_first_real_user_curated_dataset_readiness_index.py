from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = (
    PROJECT_ROOT / "docs" / "first_real_user_curated_dataset_readiness_index.md"
)


def test_first_real_user_curated_dataset_readiness_index_covers_contract() -> None:
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
        "no predictor clinico",
        "plataforma de priorizacion terapeutica",
        "no validacion clinica",
        "no validacion experimental",
        "no uso clinico",
        "revision experta",
        "validacion experimental",
        "riesgo no resuelto",
        "teoria de nodos funcionales",
        "multi-organismo",
        "score alto no equivale automaticamente a confianza alta",
        "score alto",
        "confianza alta",
        "evidencia local",
        "literatura externa",
        "procedencia",
        "primer dataset real",
    ]:
        assert phrase in text

    for document_name in [
        "real_user_curated_dataset_validation.md",
        "real_user_operational_guide.md",
        "real_user_curated_dataset_checklist.md",
        "user_curated_portable_validation_phase_index.md",
        "internal_release_readiness_2026_05_27.md",
        "user_curated_interpretation_phase_closure.md",
        "methodology.md",
        "data_model.md",
        "readme.md",
    ]:
        assert document_name in text

    assert "PowerShell" in raw_text
