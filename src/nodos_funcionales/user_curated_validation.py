from __future__ import annotations

import csv
from pathlib import Path


USER_CURATED_MANIFEST_COLUMNS = [
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

REQUIRED_USER_CURATED_MANIFEST_FIELDS = {
    "organism",
    "dataset_id",
    "input_file",
}

FORBIDDEN_USER_CURATED_DEFAULTS = {
    "PAO1",
    "H37Rv",
    "Corynebacterium",
    "Pseudomonas aeruginosa",
    "Mycobacterium tuberculosis",
}


def validate_user_curated_manifest(path: str | Path) -> list[str]:
    """Validate a user-curated dataset manifest without mutating project state."""
    manifest_path = Path(path)
    errors: list[str] = []

    if not manifest_path.exists():
        return [f"Manifest file does not exist: {manifest_path}"]
    if not manifest_path.is_file():
        return [f"Manifest path is not a file: {manifest_path}"]

    try:
        content = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Manifest file could not be read: {manifest_path}: {exc}"]

    for forbidden_default in FORBIDDEN_USER_CURATED_DEFAULTS:
        if forbidden_default in content:
            errors.append(f"Manifest contains forbidden organism default: {forbidden_default}")

    try:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != USER_CURATED_MANIFEST_COLUMNS:
                errors.append(
                    "Manifest columns must match expected contract exactly: "
                    + ", ".join(USER_CURATED_MANIFEST_COLUMNS)
                )
                return errors

            rows = list(reader)
    except csv.Error as exc:
        return [*errors, f"Manifest CSV could not be parsed: {exc}"]

    if not rows:
        errors.append("Manifest must contain at least one dataset row.")
        return errors

    for row_index, row in enumerate(rows, start=2):
        source_type = _clean(row.get("source_type"))
        if source_type != "user_curated":
            errors.append(f"Row {row_index}: source_type must be user_curated.")

        for field in sorted(REQUIRED_USER_CURATED_MANIFEST_FIELDS):
            if not _clean(row.get(field)):
                errors.append(f"Row {row_index}: {field} must not be empty.")

    return errors


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()
