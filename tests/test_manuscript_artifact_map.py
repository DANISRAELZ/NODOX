from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "manuscript_artifact_map.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_manuscript_artifact_map_exists() -> None:
    assert DOC_PATH.exists()


def test_manuscript_artifact_map_required_artifacts_and_boundaries() -> None:
    text = _text()
    required_terms = [
        "figure 1: functional nodes conceptual framework",
        "figure 2: user_curated workflow",
        "figure 3: gui execution and run-review workflow",
        "figure 4 or supplementary figure: isolated publication package structure",
        "table 1: model variables and interpretation",
        "table 2: evidence/provenance classes",
        "table 3: tests and validation boundaries",
        "table 4: demo outputs and interpretation",
        "supplementary material: reproducibility checklist",
        "supplementary material: gui workflow validation",
        "manuscript-support artifacts and not biological validation by themselves",
        "do not establish biological validation",
        "clinical validation",
        "experimental confirmation",
    ]
    for term in required_terms:
        assert term in text
