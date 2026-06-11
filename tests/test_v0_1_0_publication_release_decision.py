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
        "clinically validated platform",
        "experimentally validated platform",
        "git tag v0.1.0-publication",
    ]
    for term in required_terms:
        assert term in text
