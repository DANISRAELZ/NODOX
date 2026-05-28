from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_portable_validation_phase_index.md"


def test_user_curated_portable_validation_phase_index_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "user_curated",
        "portable validation",
        "multi-organism",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient evidence",
        "conservative interpretation",
        "provenance",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
        "no clinical validation",
        "no experimental validation",
        "safe_target",
        "clinically_valid",
        "validated_clinically",
        "validated_experimentally",
        "scoring.py",
        "dbfa079",
        "470ba33",
        "14df878",
        "9058e72",
        "8841909",
        "504c1af",
    ]:
        assert phrase in text

    for organism_token in [
        "PAO1",
        "H37Rv",
        "Corynebacterium",
    ]:
        assert organism_token in raw_text

    for tag in [
        "user-curated-pipeline-integration-validation-2026-05-27",
        "user-curated-final-reporting-interpretation-validation-2026-05-27",
        "user-curated-final-reporting-interpretation-closure-2026-05-27",
        "user-curated-minimal-functional-validation-flow-2026-05-27",
        "user-curated-minimal-functional-validation-flow-closure-2026-05-27",
        "user-curated-multiorganism-decoupling-audit-2026-05-27",
    ]:
        assert tag in text
