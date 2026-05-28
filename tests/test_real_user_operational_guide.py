from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "real_user_operational_guide.md"


def test_real_user_operational_guide_exists_and_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "real user",
        "user_curated",
        "organism_profile",
        "gene_list",
        "functional_annotations",
        "evolutionary_escape_risk",
        "manual_curation",
        "evidence_quality",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient evidence",
        "conservative interpretation",
        "provenance",
        "demo",
        "proxy",
        "cache",
        "online",
        "controlled_reference",
        "no clinical validation",
        "no experimental validation",
        "not a clinical predictor",
        "safe_target",
        "clinically_valid",
        "validated_clinically",
        "validated_experimentally",
        "pytest",
    ]:
        assert phrase in text

    assert "PowerShell" in raw_text
