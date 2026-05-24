from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_interpretation_release_closure.md"


def test_user_curated_interpretation_release_closure_document_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8").lower()

    for phrase in [
        "user_curated",
        "score_confidence_interpretation",
        "conservative_interpretation",
        "final_interpretation_matrix",
        "exportacion",
        "fixture minimo",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "src/nodos_funcionales/scoring.py",
        "pesos",
        "formulas",
        "ranking",
        "demo",
        "proxy",
        "cache",
        "controlled_reference",
        "online",
        "validacion experimental",
        "herramienta clinica",
        "predictor definitivo",
        "evidencia insuficiente no equivale a bajo riesgo",
        "riesgo evolutivo incierto no equivale a bajo riesgo evolutivo",
        "multiorganismo",
    ]:
        assert phrase in text

    for forbidden_default in [
        "corynebacterium por defecto",
        "pao1 por defecto",
        "h37rv por defecto",
        "valor por defecto corynebacterium",
        "valor por defecto pao1",
        "valor por defecto h37rv",
    ]:
        assert forbidden_default not in text
