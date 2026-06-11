from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "gui_module_closure_2026_06_11.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_gui_module_closure_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_gui_module_closure_required_concepts() -> None:
    text = _text()
    required_terms = [
        "gui module closure",
        "user_curated",
        "quality gate",
        "conservative interpretation",
        "controlled pipeline execution",
        "isolated gui runs",
        "results/gui_runs/<run_id>/",
        "logs and outputs",
        "publication_package",
        "review",
        "comparison output restricted to `review/`",
        "no clinical validation",
        "experimental validation",
        "no further gui feature expansion is recommended before publication",
        "commercial-grade deployment",
        "multi-user server",
    ]
    for term in required_terms:
        assert term in text
