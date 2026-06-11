from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "dependency_security_review.md"


def test_dependency_security_review_optional_workflow_boundary() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "core install does not require snakemake",
        "optional workflow dependencies",
        "separate transitive license/security review requirements",
        "public workflow distribution remains blocked until optional workflow dependency review is completed",
        "unknown snakemake transitive dependency metadata does not block the core release",
        "known vulnerabilities",
        "not imply clinical validation",
        "experimental validation",
        "biological validation",
    ]
    for term in required_terms:
        assert term in text
