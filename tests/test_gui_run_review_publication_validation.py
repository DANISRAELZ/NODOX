from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "gui_run_review_publication_validation.md"


def _doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_gui_run_review_publication_validation_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_gui_run_review_publication_validation_doc_contract() -> None:
    text = _doc_text()
    required_terms = [
        "isolated gui runs",
        "results/gui_runs/<run_id>/",
        "publication_package",
        "comparison output writes only to `review/`",
        "generated publication packages must remain inside the selected gui run directory",
        "score ranking is not experimental validation",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "`therapeutic_priority_score` and `evidence_confidence_score` must remain distinct",
        "`user_curated` evidence is curator-provided evidence",
        "not automatically external validation",
        "workflow validation",
        "not biological validation",
        "not clinical validation",
    ]
    for term in required_terms:
        assert term in text


def test_gui_run_review_publication_validation_doc_write_boundaries() -> None:
    text = _doc_text()
    assert "results/gui_runs/<run_id>/publication_package/" in text
    assert "results/gui_runs/<run_id>/review/" in text
    assert "must not overwrite the base package" in text
    assert "results/publication_package/" in text
    assert "config/taxon_resolution_cache.json" in text
