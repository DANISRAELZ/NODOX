from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = PROJECT_ROOT / "docs" / "release_notes_v0_1_0_publication.md"


def test_release_notes_v0_1_0_publication_content() -> None:
    text = NOTES_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "v0.1.0-publication",
        "2026-06-11",
        "release scope",
        "included",
        "not included",
        "validation status",
        "intended use",
        "not intended",
        "gui",
        "user_curated",
        "publication_package",
        "limitations",
        "no clinical validation",
        "no experimental validation",
        "not intended for clinical decision-making",
        "do not confirm therapeutic validity",
    ]
    for term in required_terms:
        assert term in text
