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
