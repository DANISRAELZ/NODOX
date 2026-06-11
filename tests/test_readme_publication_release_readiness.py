from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
README_PATH = PROJECT_ROOT / "README.md"


def test_readme_publication_release_readiness_terms() -> None:
    text = README_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "nodos funcionales",
        "functional nodes",
        "prioritization",
        "user_curated",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "gui",
        "publication_package",
        "pseudomonas aeruginosa",
        "citation.cff",
        "project code is licensed under apache license 2.0",
        "dependency license and security review remain release requirements",
        "pre-publication repository audit",
        "ai-use transparency statement",
        "limitations",
        "no clinical validation",
        "no experimental validation",
    ]
    for term in required_terms:
        assert term in text
