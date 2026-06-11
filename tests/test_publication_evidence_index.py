from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "publication_evidence_index.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_publication_evidence_index_exists() -> None:
    assert DOC_PATH.exists()


def test_publication_evidence_index_required_claims_and_boundaries() -> None:
    text = _text()
    required_terms = [
        "theoretical foundation",
        "multi-organism orientation",
        "user_curated input workflow",
        "conservative interpretation",
        "pipeline execution",
        "gui runs are isolated",
        "publication packages are run-local",
        "comparison writes only to review",
        "testing strategy",
        "demo readiness",
        "release readiness",
        "nodos funcionales is a prioritization framework, not a clinical predictor",
        "separates therapeutic priority from evidence confidence",
        "`user_curated` evidence is curator-provided and not automatically externally validated",
        "workflow validation is not biological or experimental validation",
        "scoring results require downstream validation before biological or therapeutic claims",
        "a high `therapeutic_priority_score` does not imply a high `evidence_confidence_score`",
    ]
    for term in required_terms:
        assert term in text
