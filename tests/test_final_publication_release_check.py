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
        "offline suite",
        "v0.1.0-publication",
        "no clinical validation",
        "no experimental validation",
        "final tag not yet created",
        "manual approval",
    ]
    for term in required_terms:
        assert term in text
