from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PHRASES = [
    "clinically validated",
    "experimentally validated",
    "safe target",
    "confirmed therapeutic target",
    "validated therapeutic target",
]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_publication_manuscript_materials_exist() -> None:
    for path in [
        "docs/software_paper_draft.md",
        "docs/manuscript_tables.md",
        "docs/manuscript_figures.md",
        "docs/supplementary_methods.md",
        "docs/supplementary_tables.md",
        "docs/supplementary_validation.md",
        "docs/release_notes_publication_2026_06_10.md",
        "CITATION.cff",
    ]:
        assert (PROJECT_ROOT / path).exists(), path


def test_software_paper_contains_required_conservative_content() -> None:
    manuscript = _read("docs/software_paper_draft.md").lower()
    assert "therapeutic_priority_score" in manuscript
    assert "evidence_confidence_score" in manuscript
    assert "evolutionary_escape_risk" in manuscript
    assert "prioritized hypotheses" in manuscript or "independent validation" in manuscript
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in manuscript


def test_manuscript_supporting_docs_avoid_prohibited_language() -> None:
    for path in [
        "docs/manuscript_tables.md",
        "docs/manuscript_figures.md",
        "docs/supplementary_methods.md",
        "docs/supplementary_tables.md",
        "docs/supplementary_validation.md",
        "docs/release_notes_publication_2026_06_10.md",
    ]:
        text = _read(path).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text, f"{phrase} found in {path}"


def test_readme_publication_section_is_conservative() -> None:
    readme = _read("README.md").lower()
    assert "publication-oriented" in readme or "publication-package" in readme
    assert "therapeutic_priority_score" in readme
    assert "evidence_confidence_score" in readme
    assert "independent validation" in readme
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in readme
