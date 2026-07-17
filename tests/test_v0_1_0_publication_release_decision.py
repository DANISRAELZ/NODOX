from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "v0_1_0_publication_release_decision.md"


def test_v0_1_0_publication_release_decision_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "v0.1.0-publication",
        "final human approval",
        "dependency license and security review",
        "demo",
        "final git tag should not be created automatically",
        "no automatic",
        "technically close to `v0.1.0-publication`",
        "core release can proceed only after accepting or completing core dependency/security and sensitive-data review",
        "docs/final_public_release_audit.md",
        "docs/sensitive_data_and_secret_scan.md",
        "docs/core_dependency_review_summary.md",
        "docs/public_release_file_inclusion_review.md",
        "no clinical validation",
        "no experimental validation",
        "git tag v0.1.0-publication",
    ]
    for term in required_terms:
        assert term in text
