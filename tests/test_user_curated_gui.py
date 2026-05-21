from __future__ import annotations

import csv
from pathlib import Path

from apps.user_curated_onboarding_app import _build_expert_review_summary


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
        "Checklist visual de archivos locales",
        "Importacion validada asistida como comando manual",
        "Revision visual de calidad/evidencia",
        "Quality gate previo a scoring",
        "Resumen final exportable para revision experta",
        "_build_expert_review_summary",
        "Descargar resumen Markdown local",
        "no implica recomendacion terapeutica",
        "Un score alto, en fases futuras, no equivale automaticamente a confianza alta",
        "controlled_reference",
        "online",
        "assess_pre_scoring_readiness",
        "not_ready_for_scoring",
        "requires_expert_review",
        "conditionally_ready_for_future_controlled_scoring",
        "sin ejecutar scoring",
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
        "La GUI no ejecuta este comando",
        "un quality gate favorable no equivale a recomendacion terapeutica",
        "un scoring futuro no sustituye revision experta",
        "un score alto no equivale automaticamente a confianza alta",
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
        "Importacion validada asistida como comando manual",
        "Quality gate previo a scoring",
        "Resumen final exportable",
        "Markdown",
        "recomendacion terapeutica",
        "quality gate",
        "not_ready_for_scoring",
        "requires_expert_review",
        "conditionally_ready_for_future_controlled_scoring",
        "sin ejecutar scoring",
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


def test_user_curated_onboarding_gui_final_flow_order() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_text = (project_root / "apps" / "user_curated_onboarding_app.py").read_text(
        encoding="utf-8"
    )
    expected_headers = [
        'st.header("1. Crear staging local")',
        'st.header("2. Revisar archivos locales")',
        'st.header("3. Validar manifest")',
        'st.header("4. Revision visual de calidad/evidencia del dataset")',
        'st.header("5. Quality gate previo a scoring")',
        'st.header("6. Resumen final exportable para revision experta")',
        'st.header("7. Importacion validada asistida como comando manual")',
    ]

    positions = [app_text.index(header) for header in expected_headers]
    assert positions == sorted(positions)
    assert "Revisar preparacion para scoring" not in app_text
    assert "Importar dataset (deshabilitado en esta version)" not in app_text


def test_user_curated_expert_review_summary_is_downloadable_markdown(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    raw_inputs = tmp_path / "raw_inputs"
    raw_inputs.mkdir()
    (raw_inputs / "example_dataset.csv").write_text("protein_id,gene\nP1,gene_a\n", encoding="utf-8")

    columns = [
        "organism",
        "strain",
        "dataset_id",
        "dataset_version",
        "curator_name",
        "curation_date",
        "source_type",
        "evidence_status",
        "evidence_kind",
        "provenance",
        "input_file",
        "input_schema",
        "required_for_scoring",
        "notes",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(
            {
                "organism": "Example bacterium",
                "strain": "isolate-1",
                "dataset_id": "example_dataset",
                "dataset_version": "2026-05-21",
                "curator_name": "reviewer",
                "curation_date": "2026-05-21",
                "source_type": "user_curated",
                "evidence_status": "reviewed",
                "evidence_kind": "experimental",
                "provenance": "Reviewed local record accession ABC123",
                "input_file": "raw_inputs/example_dataset.csv",
                "input_schema": "data_templates/gene_list_template.csv",
                "required_for_scoring": "true",
                "notes": "Prepared for expert review summary.",
            }
        )

    summary = _build_expert_review_summary(manifest_path)
    markdown = summary["markdown"]

    assert summary["dataset_ids"] == ["example_dataset"]
    assert summary["manifest_status"] == "valido estructuralmente"
    assert summary["quality_gate"]["status"] == "conditionally_ready_for_future_controlled_scoring"
    assert summary["import_command"]
    assert "fila 2: detectado (raw_inputs/example_dataset.csv)" in summary["detected_files"]
    assert "# Resumen final user_curated para revision experta" in markdown
    assert "decision_final: conditionally_ready_for_future_controlled_scoring" in markdown
    assert "No implica recomendacion terapeutica." in markdown
    assert "No sustituye revision experta." in markdown
    assert "Un score alto, en fases futuras, no equivale automaticamente a confianza alta." in markdown
    assert "No mezclar user_curated con demo, proxy, cache, controlled_reference u online." in markdown
    assert "Comando manual sugerido para importacion validada" in markdown


def test_user_curated_expert_review_summary_hides_import_command_until_gate_applies(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text(
        "\n".join(
            [
                "organism,strain,dataset_id,dataset_version,curator_name,curation_date,"
                "source_type,evidence_status,evidence_kind,provenance,input_file,"
                "input_schema,required_for_scoring,notes",
                "Example bacterium,isolate-1,example_dataset,2026-05-21,reviewer,"
                "2026-05-21,user_curated,pending,experimental,pending,"
                "raw_inputs/example_dataset.csv,data_templates/gene_list_template.csv,"
                "true,Awaiting expert review",
            ]
        ),
        encoding="utf-8",
    )

    summary = _build_expert_review_summary(manifest_path)

    assert summary["quality_gate"]["status"] == "requires_expert_review"
    assert summary["import_command"] is None
    assert "No se sugiere todavia" in summary["markdown"]


def test_user_curated_quality_gate_documentation_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    doc_path = project_root / "docs" / "user_curated_pre_scoring_quality_gate.md"
    template_path = (
        project_root / "docs" / "templates" / "user_curated_pre_scoring_approval_template.md"
    )

    assert doc_path.exists()
    assert template_path.exists()

    combined_text = "\n".join(
        [
            doc_path.read_text(encoding="utf-8"),
            template_path.read_text(encoding="utf-8"),
        ]
    )
    required_terms = {
        "quality gate",
        "pre-scoring approval",
        "not_ready_for_scoring",
        "requires_expert_review",
        "conditionally_ready_for_future_controlled_scoring",
        "project_id",
        "organism",
        "strain_or_isolate",
        "dataset_id",
        "reviewer",
        "review_date",
        "manifest_path",
        "source_type_confirmed",
        "evidence_status_reviewed",
        "provenance_reviewed",
        "raw_inputs_reviewed",
        "demo_proxy_cache_absent",
        "missing_fields_accepted",
        "limitations_acknowledged",
        "expert_review_status",
        "approval_status",
        "approval_notes",
        "no ejecuta scoring",
        "no ejecuta pipeline",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "revision experta",
        "validacion experimental",
    }
    normalized_text = " ".join(combined_text.split())
    for term in required_terms:
        assert term in normalized_text

    forbidden_phrases = {
        "clinically_valid",
        "therapeutically_validated",
    }
    for forbidden_phrase in forbidden_phrases:
        assert forbidden_phrase not in combined_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in combined_text
