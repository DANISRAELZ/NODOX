from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "internal_release_readiness_2026_05_27.md"


def test_internal_release_readiness_document_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "internal release readiness",
        "user_curated",
        "theory-first",
        "multi-organism",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "conservative interpretation",
        "insufficient evidence",
        "provenance",
        "demo",
        "proxy",
        "cache",
        "online",
        "controlled_reference",
        "no clinical validation",
        "no experimental validation",
        "not a clinical predictor",
        "pytest",
        "scoring.py",
    ]:
        assert phrase in text

    for organism_token in [
        "PAO1",
        "H37Rv",
        "Corynebacterium",
    ]:
        assert organism_token in raw_text
