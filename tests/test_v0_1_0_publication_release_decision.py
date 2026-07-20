from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "v0_1_0_publication_release_decision.md"


def test_v0_1_0_publication_release_decision_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "final release version: `0.1.0`",
        "final release tag: `v0.1.0`",
        "release date: `2026-07-20`",
        "repository owner approved",
        "no orcid is included",
        "demo",
        "strict complete pytest suite",
        "clean-clone quick start smoke test",
        "public-release inventory workflow",
        "no clinical validation",
        "no experimental validation",
        "team of collaborators",
        "project code is licensed under apache license 2.0",
        "git tag v0.1.0",
        "merged release commit on `main`",
    ]
    for term in required_terms:
        assert term in text
