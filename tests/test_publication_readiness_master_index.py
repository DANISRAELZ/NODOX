from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "publication_readiness_master_index.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_publication_readiness_master_index_exists() -> None:
    assert DOC_PATH.exists()


def test_publication_readiness_master_index_references_readiness_documents() -> None:
    text = _text()
    required_terms = [
        "docs/gui_module_closure_2026_06_11.md",
        "docs/publication_evidence_index.md",
        "docs/final_reproducible_demo_readiness.md",
        "docs/software_release_readiness_checklist.md",
        "docs/manuscript_artifact_map.md",
        "final demo",
        "manuscript",
        "release tag",
        "software citation",
        "publication-readiness-closure-2026-06-11",
    ]
    for term in required_terms:
        assert term in text
