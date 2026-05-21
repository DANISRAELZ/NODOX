from __future__ import annotations

import csv
from pathlib import Path


EXPECTED_MANIFEST_COLUMNS = [
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

REQUIRED_PLACEHOLDERS = {
    "<organism_name>",
    "<strain_or_isolate>",
    "<dataset_id>",
}

FORBIDDEN_ORGANISM_DEFAULTS = {
    "PAO1",
    "H37Rv",
    "Corynebacterium",
    "Pseudomonas aeruginosa",
    "Mycobacterium tuberculosis",
}

USER_CURATED_ENTRY_TEMPLATES = {
    "functional_annotations_template.csv": {
        "organism",
        "strain",
        "protein_id",
        "gene",
        "functional_annotation",
        "source_database",
        "evidence_status",
    },
    "gene_list_template.csv": {
        "organism",
        "strain",
        "protein_id",
        "gene",
        "source_database",
        "evidence_status",
    },
    "conservation_template.csv": {
        "organism",
        "strain",
        "protein_id",
        "gene",
        "conservation_scope",
        "source_database",
        "evidence_status",
    },
    "virulence_template.csv": {
        "protein_id",
        "gene",
        "virulence_score",
        "virulence_factor",
        "database",
    },
    "essentiality_template.csv": {
        "protein_id",
        "gene",
        "essential",
        "evidence",
        "database",
    },
    "external_sources_template.csv": {
        "organism",
        "strain",
        "protein_id",
        "gene",
        "source_database",
        "source_record_id",
        "evidence_status",
    },
    "manual_curation_template.csv": {
        "organism",
        "strain",
        "protein_id",
        "gene",
        "curator_name",
        "curation_decision",
        "evidence_status",
    },
    "user_curated_dataset_manifest_template.csv": set(EXPECTED_MANIFEST_COLUMNS),
}


def test_user_curated_dataset_manifest_template_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    template_path = project_root / "data_templates" / "user_curated_dataset_manifest_template.csv"

    assert template_path.exists()

    with template_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows
    assert rows[0] == EXPECTED_MANIFEST_COLUMNS
    assert len(rows) >= 2

    example_values = set(rows[1])
    assert REQUIRED_PLACEHOLDERS <= example_values

    template_text = template_path.read_text(encoding="utf-8")
    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in template_text


def test_user_curated_staging_readme_template_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    template_path = project_root / "docs" / "templates" / "user_curated_staging_README_template.md"

    assert template_path.exists()

    template_text = template_path.read_text(encoding="utf-8")
    required_fields = {
        "project_id",
        "organism",
        "strain_or_isolate",
        "curator",
        "date_created",
        "manifest_path",
        "raw_inputs_summary",
        "provenance_summary",
        "excluded_or_missing_data",
        "validation_status",
        "notes",
    }
    for field in required_fields:
        assert field in template_text

    required_warnings = {
        "Do not version real, private, clinical, sensitive, or unreleased data.",
        "Do not mix demo, proxy, cache, online, or `controlled_reference` material",
        "Do not run scoring or pipeline before manual review",
        "Do not interpret manifest prevalidation as biological, therapeutic, or",
        "clinical validation.",
    }
    for warning in required_warnings:
        assert warning in template_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in template_text


def test_first_user_curated_dataset_startup_document_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    doc_path = project_root / "docs" / "first_user_curated_dataset_startup.md"

    assert doc_path.exists()

    doc_text = doc_path.read_text(encoding="utf-8")
    required_terms = {
        "user_curated_staging",
        "create_user_curated_staging.py",
        "manifest.csv",
        "README.md",
        "raw_inputs",
        "provenance",
        "notes",
        "source_type=user_curated",
        "git status --short",
    }
    for term in required_terms:
        assert term in doc_text

    required_warnings = {
        "sin versionar datos reales",
        "No ejecutar",
        "pipeline",
        "scoring",
        "demo, proxy, cache",
        "user_curated",
        "validacion biologica",
        "terapeutica",
        "clinica",
    }
    for warning in required_warnings:
        assert warning in doc_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in doc_text


def test_user_friendly_onboarding_document_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    doc_path = project_root / "docs" / "user_friendly_onboarding.md"

    assert doc_path.exists()

    doc_text = doc_path.read_text(encoding="utf-8")
    required_terms = {
        "Nodos Funcionales",
        "user_curated",
        "manifest",
        "staging local",
        "create_user_curated_staging.py",
        "validate_user_curated_manifest",
        "import_dataset.py",
        "--validate-user-curated-manifest",
        "PowerShell",
        "ExecutionPolicy Bypass",
    }
    for term in required_terms:
        assert term in doc_text

    doc_text_lower = doc_text.lower()
    required_guidance = {
        "primer uso recomendado",
        "errores frecuentes",
        "l\u00edmites de interpretaci\u00f3n",
        "no ejecutar pipeline",
        "no ejecutar scoring",
        "no versionar datos reales",
        "prevalidar no es validacion biologica",
        "un score alto no equivale a validacion clinica",
        "requiere revision experta y validacion experimental",
        "quality gate",
        "not_ready_for_scoring",
        "requires_expert_review",
        "conditionally_ready_for_future_controlled_scoring",
        "resumen final exportable",
        "recomendacion terapeutica",
        "score alto, en fases futuras, no equivale",
        "flujo final",
        "importacion validada asistida como comando manual",
        "demo local controlada",
        "user_curated_gui_local_demo_checklist.md",
        "user_curated_gui_final_closure.md",
    }
    for guidance in required_guidance:
        assert guidance in doc_text_lower

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in doc_text


def test_user_curated_pre_scoring_quality_gate_templates_contract() -> None:
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


def test_user_curated_onboarding_streamlit_app_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_path = project_root / "apps" / "user_curated_onboarding_app.py"

    assert app_path.exists()

    app_text = app_path.read_text(encoding="utf-8")
    required_terms = {
        "streamlit",
        "create_staging",
        "validate_user_curated_manifest",
        "manifest.csv",
        "project_id",
        "no ejecuta pipeline",
        "no ejecuta scoring",
        "No versionar datos reales",
        "Importacion validada asistida como comando manual",
    }
    for term in required_terms:
        assert term in app_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in app_text


def test_user_curated_entry_templates_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    templates_dir = project_root / "data_templates"

    for template_name, required_columns in USER_CURATED_ENTRY_TEMPLATES.items():
        template_path = templates_dir / template_name
        assert template_path.exists(), template_name

        with template_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))

        assert rows, template_name
        header = set(rows[0])
        assert required_columns <= header

        template_text = template_path.read_text(encoding="utf-8")
        for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
            assert forbidden_default not in template_text

    manifest_columns = set(
        (templates_dir / "user_curated_dataset_manifest_template.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
        .split(",")
    )
    assert {"dataset_id", "source_type", "input_file", "input_schema"} <= manifest_columns
