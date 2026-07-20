from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
README_PATH = PROJECT_ROOT / "README.md"


def test_readme_publication_release_readiness_terms() -> None:
    readme = README_PATH.read_text(encoding="utf-8").lower()
    required_readme_terms = [
        "nodox",
        "functional nodes",
        "prioritization",
        "user-curated",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "publication-oriented",
        "pseudomonas aeruginosa",
        "citation.cff",
        "apache license 2.0",
        "limitations",
        "not experimental or clinical validation",
        "requires independent validation",
    ]
    for term in required_readme_terms:
        assert term in readme

    release_documents = {
        "pre-publication repository audit": "docs/pre_publication_repository_audit.md",
        "ai-use transparency statement": "docs/ai_use_transparency_statement.md",
        "final public release audit": "docs/final_publication_release_check.md",
        "sensitive data and secret scan": "docs/sensitive_data_and_secret_scan.md",
        "core dependency review summary": "docs/core_dependency_review_summary.md",
        "public release file inclusion review": "docs/public_release_file_inclusion_review.md",
    }
    for expected_term, relative_path in release_documents.items():
        path = PROJECT_ROOT / relative_path
        assert path.exists(), relative_path
        assert expected_term in path.read_text(encoding="utf-8").lower()

    final_check = (PROJECT_ROOT / "docs" / "final_publication_release_check.md").read_text(encoding="utf-8").lower()
    assert "public tag remains blocked until final human approval" in final_check
