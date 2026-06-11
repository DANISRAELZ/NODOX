from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "ai_use_transparency_statement.md"


def test_ai_use_transparency_statement_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "ai tools may have assisted",
        "drafting",
        "refactoring",
        "testing",
        "documentation organization",
        "human review",
        "scientific interpretation",
        "code acceptance",
        "validation boundaries",
        "licensing",
        "privacy",
        "final release decisions",
        "does not constitute biological validation",
        "clinical validation",
        "experimental validation",
        "authorship",
        "external evidence",
        "does not replace scientific responsibility",
        "journal",
        "repository",
    ]
    for term in required_terms:
        assert term in text
