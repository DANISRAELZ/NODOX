from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "final_reproducible_demo_readiness.md"
DEMO_DIR = PROJECT_ROOT / "examples" / "pseudomonas_aeruginosa_publication_demo"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_final_reproducible_demo_readiness_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_final_reproducible_demo_readiness_required_concepts() -> None:
    text = _text()
    required_terms = [
        "pseudomonas aeruginosa",
        "reproducibility",
        "expected input directory",
        "expected inputs",
        "expected outputs",
        "ranking_nodos.csv",
        "report_phase2.md",
        "publication_package",
        "does not establish biological validation",
        "clinical validation",
        "experimental validation",
        "workflow readiness",
    ]
    for term in required_terms:
        assert term in text


def test_pseudomonas_publication_demo_basic_structure_is_present() -> None:
    assert DEMO_DIR.is_dir()
    assert (DEMO_DIR / "README.md").is_file()
    assert (DEMO_DIR / "run_demo.ps1").is_file()
    assert (DEMO_DIR / "run_demo.sh").is_file()
    assert (DEMO_DIR / "input" / "manifest.yaml").is_file()
    assert (DEMO_DIR / "input" / "gene_list.csv").is_file()
    assert (DEMO_DIR / "expected_tables" / "ranking_nodos.csv").is_file()
    assert (DEMO_DIR / "expected_tables" / "report_phase2.md").is_file()
