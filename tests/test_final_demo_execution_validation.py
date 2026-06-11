from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "final_demo_execution_validation.md"
DEMO_DIR = PROJECT_ROOT / "examples" / "pseudomonas_aeruginosa_publication_demo"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_final_demo_execution_validation_doc_exists() -> None:
    assert DOC_PATH.exists()


def test_final_demo_execution_validation_doc_contract() -> None:
    text = _text()
    required_terms = [
        "pseudomonas aeruginosa",
        "examples/pseudomonas_aeruginosa_publication_demo",
        "ranking_nodos.csv",
        "report_phase2.md",
        "publication_package",
        "offline execution",
        "reproducible",
        "workflow reproducibility",
        "input/output traceability",
        "no biological validation",
        "no clinical validation",
        "no experimental validation",
        "does not validate therapeutic targets",
    ]
    for term in required_terms:
        assert term in text


def test_final_demo_directory_basic_structure_is_present() -> None:
    assert DEMO_DIR.is_dir()
    assert (DEMO_DIR / "input").is_dir()
    assert (DEMO_DIR / "expected_tables").is_dir()
    assert (DEMO_DIR / "run_demo.ps1").is_file()
    assert (DEMO_DIR / "run_demo.sh").is_file()
    assert (DEMO_DIR / "input" / "manifest.yaml").is_file()
    assert (DEMO_DIR / "expected_tables" / "ranking_nodos.csv").is_file()
    assert (DEMO_DIR / "expected_tables" / "report_phase2.md").is_file()
