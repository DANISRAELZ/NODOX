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
