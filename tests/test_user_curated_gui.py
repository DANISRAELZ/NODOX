from __future__ import annotations

from pathlib import Path


FORBIDDEN_ORGANISM_DEFAULTS = {
    "PAO1",
    "H37Rv",
    "Corynebacterium",
    "Pseudomonas aeruginosa",
    "Mycobacterium tuberculosis",
}


def test_user_curated_onboarding_gui_app_text_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_path = project_root / "apps" / "user_curated_onboarding_app.py"

    assert app_path.exists()

    app_text = app_path.read_text(encoding="utf-8")
    required_terms = {
        "streamlit",
        "ModuleNotFoundError",
        "create_staging",
        "validate_user_curated_manifest",
        "project_id",
        "README.md",
        "manifest.csv",
        "raw_inputs/",
        "notes/",
        "provenance/",
        "no ejecuta pipeline",
        "no ejecuta scoring",
        "No versionar datos reales",
        "validacion biologica",
        "Importar dataset (deshabilitado en esta version)",
    }
    for term in required_terms:
        assert term in app_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in app_text


def test_user_curated_onboarding_gui_document_text_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    doc_path = project_root / "docs" / "user_curated_gui_onboarding.md"

    assert doc_path.exists()

    doc_text = doc_path.read_text(encoding="utf-8")
    required_terms = {
        "Streamlit",
        "streamlit run apps/user_curated_onboarding_app.py",
        "pip install streamlit",
        "no ejecuta scoring",
        "no ejecuta pipeline",
        "no genera outputs cientificos",
        "revision experta",
        "no sustituye",
    }
    for term in required_terms:
        assert term in doc_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in doc_text
