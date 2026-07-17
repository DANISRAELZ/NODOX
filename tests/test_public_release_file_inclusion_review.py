from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "public_release_file_inclusion_review.md"


def test_public_release_file_inclusion_review_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "safe/expected",
        "source code",
        "tests",
        "documentation",
        "safe fixtures",
        "safe demo examples",
        "readme.md",
        "citation.cff",
        "license",
        "changelog.md",
        "release notes",
        "conditional",
        "demo outputs",
        "generated publication packages",
        "dependency inventories",
        "manuscript artifacts",
        "optional workflow files",
        "exclude unless explicitly approved",
        ".env",
        "credentials",
        "raw prompts/transcripts",
        "unreviewed logs",
        "uncontrolled `results/`",
        "uncontrolled `data_sessions/`",
        "uncontrolled `data_processed/`",
        "local caches",
        "patient data",
        "confidential institutional data",
        "real unpublished datasets without consent",
    ]
    for term in required_terms:
        assert term in text
