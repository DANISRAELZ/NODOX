from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = PROJECT_ROOT / "docs" / "final_publication_release_check.md"


def test_final_publication_release_check_content() -> None:
    text = CHECK_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "readme",
        "citation.cff",
        "changelog",
        "release notes",
        "license",
        "demo",
        "gui",
        "publication evidence",
        "final demo execution validation",
        "demo expected outputs manifest",
        "manuscript figure/table specifications",
        "release decision",
        "offline suite",
        "pre-publication repository audit requirements",
        "docs/pre_publication_repository_audit.md",
        "docs/public_release_exclusion_policy.md",
        "docs/ai_use_transparency_statement.md",
        "docs/repository_hygiene_checklist.md",
        "docs/final_public_release_audit.md",
        "docs/sensitive_data_and_secret_scan.md",
        "docs/core_dependency_review_summary.md",
        "docs/public_release_file_inclusion_review.md",
        "final public release is blocked until",
        "project code is licensed under apache license 2.0",
        "dependency license and security review remain release requirements",
        "project code license is apache license 2.0",
        "dependency review is complete",
        "sensitive data review is complete",
        "internal prompts/logs are removed or excluded",
        "ai-use transparency statement is reviewed",
        "human approval is given",
        "core release can proceed only after accepting or completing core dependency/security and sensitive-data review",
        "v0.1.0-publication",
        "no clinical validation",
        "no experimental validation",
        "final tag not yet created",
        "manual approval",
    ]
    for term in required_terms:
        assert term in text
