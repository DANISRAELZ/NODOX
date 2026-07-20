from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"


def test_changelog_publication_release_entry() -> None:
    text = CHANGELOG_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "v0.1.0",
        "2026-07-20",
        "gui",
        "user_curated",
        "publication_package",
        "known limitations",
        "no clinical validation",
        "no experimental validation",
        "do not confirm therapeutic validity",
        "team of collaborators",
        "apache license 2.0",
    ]
    for term in required_terms:
        assert term in text
    assert "validated therapeutic target" not in text
