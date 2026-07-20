from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CITATION_PATH = PROJECT_ROOT / "CITATION.cff"


def test_citation_cff_publication_metadata() -> None:
    text = CITATION_PATH.read_text(encoding="utf-8").lower()
    assert "cff-version" in text
    assert 'title: "nodox"' in text
    assert 'version: "0.1.0"' in text
    assert "dan israel" in text
    assert "zavala vargas" in text
    assert "2026-07-20" in text
    assert "orcid" not in text
    assert "doi:" not in text
    assert "10.xxxx" not in text
    assert "placeholder doi" not in text
    assert "clinically validated" not in text
    assert "experimentally validated" not in text
    assert "validated therapeutic target" not in text
