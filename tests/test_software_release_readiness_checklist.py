from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "software_release_readiness_checklist.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_software_release_readiness_checklist_exists() -> None:
    assert DOC_PATH.exists()


def test_software_release_readiness_checklist_required_items() -> None:
    text = _text()
    required_terms = [
        "readme",
        "installation",
        "reproducibility",
        "tests",
        "demo",
        "gui",
        "citation.cff",
        "license",
        "changelog",
        "release notes",
        "version tag",
        "v0.1.0-publication",
        "limitations",
    ]
    for term in required_terms:
        assert term in text
