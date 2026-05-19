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
        "Que hace esta GUI",
        "Que NO hace esta GUI",
        "project_id",
        "user_curated_staging",
        "README.md",
        "manifest.csv",
        "raw_inputs/",
        "notes/",
        "provenance/",
        "no ejecuta pipeline",
        "no ejecuta scoring",
        "no genera outputs cientificos",
        "No versionar datos reales",
        "validacion biologica",
        "validacion clinica",
        "suficiencia cientifica",
        "revision experta",
        "Importar dataset (deshabilitado en esta version)",
    }
    for term in required_terms:
        assert term in app_text

    forbidden_runtime_calls = {
        "subprocess",
        "run_pipeline.py",
        "import_dataset.py --",
        "import import_dataset",
        "from import_dataset",
    }
    for forbidden_call in forbidden_runtime_calls:
        assert forbidden_call not in app_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in app_text


def test_user_curated_onboarding_gui_document_text_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    doc_path = project_root / "docs" / "user_curated_gui_onboarding.md"

    assert doc_path.exists()

    doc_text = doc_path.read_text(encoding="utf-8")
    normalized_doc_text = " ".join(doc_text.split())
    required_terms = {
        "Streamlit",
        "Streamlit es una dependencia opcional",
        "Que hace esta GUI",
        "Que NO hace esta GUI",
        "streamlit run apps/user_curated_onboarding_app.py",
        "pip install streamlit",
        "no ejecuta scoring",
        "no ejecuta pipeline",
        "no genera outputs cientificos",
        "no valida biologicamente",
        "no valida clinicamente",
        "revision experta",
        "no sustituye",
        "raw_inputs",
        "provenance",
        "notes",
        "user_curated_staging",
    }
    for term in required_terms:
        assert term in normalized_doc_text

    required_optional_dependency_terms = {
        "No se agrega Streamlit a las dependencias globales",
        "Streamlit sigue siendo opcional",
        "dependencia obligatoria",
    }
    for term in required_optional_dependency_terms:
        assert term in normalized_doc_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in doc_text
