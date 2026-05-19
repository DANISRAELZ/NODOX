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
        "Checklist visual de preparacion",
        "Importacion validada asistida",
        "Revision visual de calidad/evidencia",
        "Limites interpretativos",
        "La GUI se detiene aqui",
        "project_id",
        "user_curated_staging",
        "README.md",
        "manifest.csv",
        "evidence_status",
        "evidence_kind",
        "provenance",
        "required_for_scoring",
        "placeholders",
        "demo/proxy/cache",
        "raw_inputs/",
        "notes/",
        "provenance/",
        "no ejecuta pipeline",
        "no ejecuta scoring",
        "no ejecuta Snakemake",
        "no importa datos",
        "no genera ranking",
        "no genera outputs cientificos",
        "No versionar datos reales",
        "validacion biologica",
        "validacion clinica",
        "suficiencia cientifica",
        "revision experta",
        "confidence_score",
        "therapeutic_priority_score",
        "Listo para revision/importacion",
        "Requiere correccion antes de avanzar",
        "source_type=user_curated",
        "sin mezcla demo/proxy/cache",
        "git status revisado",
        r".\.venv\Scripts\python.exe import_dataset.py",
        "--validate-user-curated-manifest <ruta_manifest.csv>",
        "La importacion validada ocurre despues de que el manifest valida sin",
        "esta GUI solo prepara staging, valida manifest y muestra el comando manual",
        "Importar dataset (deshabilitado en esta version)",
    }
    for term in required_terms:
        assert term in app_text

    forbidden_runtime_calls = {
        "subprocess",
        "run_pipeline.py",
        "snakemake",
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
        "Checklist visual",
        "Revision visual de calidad/evidencia",
        "Importacion validada asistida",
        "La GUI se detiene aqui",
        "streamlit run apps/user_curated_onboarding_app.py",
        "pip install streamlit",
        r".\.venv\Scripts\python.exe -m streamlit run apps\user_curated_onboarding_app.py",
        "no ejecuta scoring",
        "no ejecuta pipeline",
        "no ejecuta Snakemake",
        "no genera ranking",
        "no genera outputs cientificos",
        "no valida biologicamente",
        "no valida clinicamente",
        "confidence_score",
        "therapeutic_priority_score",
        "provenance",
        "required_for_scoring",
        "placeholders",
        "demo/proxy/cache",
        "procedencia y completitud",
        "revision experta",
        "no sustituye",
        "raw_inputs",
        "provenance",
        "notes",
        "user_curated_staging",
        "import_dataset.py --validate-user-curated-manifest",
        "--validate-user-curated-manifest <ruta_manifest.csv>",
        "no lo ejecuta",
        "no forma parte obligatoria del pipeline",
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
