from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = PROJECT_ROOT / "docs" / "final_publication_release_check.md"


def test_final_publication_release_check_content() -> None:
    text = CHECK_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "target version: `0.1.0`",
        "target tag: `v0.1.0`",
        "release date: `2026-07-20`",
        "repository owner has authorized",
        "readme.md",
        "citation.cff",
        "changelog.md",
        "release notes",
        "apache license 2.0",
        "demo",
        "gui",
        "publication evidence",
        "final demo execution validation",
        "demo expected outputs manifest",
        "manuscript figure/table specifications",
        "release decision",
        "strict complete suite",
        "quick start smoke test",
        "public release inventory",
        "pre-publication repository audit requirements",
        "docs/pre_publication_repository_audit.md",
        "docs/public_release_exclusion_policy.md",
        "docs/ai_use_transparency_statement.md",
        "docs/repository_hygiene_checklist.md",
        "docs/final_public_release_audit.md",
        "docs/sensitive_data_and_secret_scan.md",
        "docs/core_dependency_review_summary.md",
        "docs/public_release_file_inclusion_review.md",
        "project code is licensed under apache license 2.0",
        "third-party data and dependencies remain governed",
        "no clinical validation",
        "no experimental validation",
        "theoretical model",
        "team of collaborators",
        "final tag points to the merged release commit",
    ]
    for term in required_terms:
        assert term in text
