from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.nodos_funcionales.user_curated_validation import (
    USER_CURATED_MANIFEST_COLUMNS,
    validate_user_curated_manifest,
)


NOT_READY_FOR_SCORING = "not_ready_for_scoring"
REQUIRES_EXPERT_REVIEW = "requires_expert_review"
CONDITIONALLY_READY_FOR_FUTURE_CONTROLLED_SCORING = (
    "conditionally_ready_for_future_controlled_scoring"
)

WEAK_PROVENANCE_VALUES = {"", "na", "n/a", "none", "unknown", "pending", "placeholder", "tbd"}
REQUIRED_CHECKLIST_FIELDS = {
    "source_type_confirmed": False,
    "evidence_status_reviewed": False,
    "provenance_reviewed": False,
    "raw_inputs_reviewed": False,
    "demo_proxy_cache_absent": False,
    "missing_fields_accepted": False,
    "limitations_acknowledged": True,
    "expert_review_status": "required",
}


def assess_pre_scoring_readiness(manifest_path: str | Path) -> dict[str, Any]:
    """Assess a user_curated manifest before any future scoring decision.

    The assessment is intentionally conservative and side-effect free. It reads
    the manifest, reuses the existing manifest validator, and returns a status,
    errors, warnings and checklist hints. It does not write files, execute
    commands, load the scoring module, or calculate scientific scores.
    """
    path = Path(manifest_path)
    errors = validate_user_curated_manifest(path)
    warnings = [
        "Este quality gate no valida biologica ni clinicamente el dataset.",
        "No ejecuta scoring, no ejecuta pipeline y no calcula therapeutic_priority_score "
        "ni evidence_confidence_score.",
        "La decision final requiere revision experta y validacion experimental futura.",
    ]
    checklist: dict[str, Any] = dict(REQUIRED_CHECKLIST_FIELDS)

    rows, read_errors = _read_manifest_rows(path)
    errors.extend(read_errors)
    if errors:
        return {
            "status": NOT_READY_FOR_SCORING,
            "errors": errors,
            "warnings": warnings,
            "checklist": checklist,
        }

    if _manifest_has_placeholders(rows):
        errors.append("Manifest contains placeholders such as <...>.")
        return {
            "status": NOT_READY_FOR_SCORING,
            "errors": errors,
            "warnings": warnings,
            "checklist": checklist,
        }

    status = CONDITIONALLY_READY_FOR_FUTURE_CONTROLLED_SCORING
    for row_index, row in enumerate(rows, start=2):
        source_type = _clean(row.get("source_type"))
        evidence_status = _clean(row.get("evidence_status")).lower()
        provenance = _clean(row.get("provenance"))
        input_file = _clean(row.get("input_file"))
        required_for_scoring = _clean(row.get("required_for_scoring"))
        manifest_text = " ".join(_clean(value).lower() for value in row.values())

        if source_type != "user_curated":
            errors.append(f"Row {row_index}: source_type must be user_curated.")
            status = NOT_READY_FOR_SCORING

        if not input_file:
            errors.append(f"Row {row_index}: input_file must be declared.")
            status = NOT_READY_FOR_SCORING

        if not required_for_scoring:
            errors.append(f"Row {row_index}: required_for_scoring must be declared.")
            status = NOT_READY_FOR_SCORING

        if "demo" in manifest_text or "proxy" in manifest_text or "cache" in manifest_text:
            warnings.append(f"Row {row_index}: possible demo/proxy/cache mixture detected.")
            status = _downgrade_to_expert_review(status)

        if evidence_status == "pending":
            warnings.append(f"Row {row_index}: evidence_status is pending.")
            status = _downgrade_to_expert_review(status)

        if provenance.lower() in WEAK_PROVENANCE_VALUES:
            warnings.append(f"Row {row_index}: provenance is empty or weak.")
            status = _downgrade_to_expert_review(status)

        # Non-structural gaps still need a human decision before future scoring.
        for field in _missing_manifest_fields(row):
            warnings.append(
                f"Row {row_index}: {field} is empty; conditional readiness requires "
                "a complete manifest row."
            )
            status = _downgrade_to_expert_review(status)

    checklist.update(
        {
            "source_type_confirmed": not any(
                _clean(row.get("source_type")) != "user_curated" for row in rows
            ),
            "evidence_status_reviewed": not any(
                _clean(row.get("evidence_status")).lower() == "pending" for row in rows
            ),
            "provenance_reviewed": not any(
                _clean(row.get("provenance")).lower() in WEAK_PROVENANCE_VALUES for row in rows
            ),
            "raw_inputs_reviewed": all(bool(_clean(row.get("input_file"))) for row in rows),
            "demo_proxy_cache_absent": not any(
                _contains_demo_proxy_cache(row) for row in rows
            ),
        }
    )

    if errors:
        status = NOT_READY_FOR_SCORING

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "checklist": checklist,
    }


def _read_manifest_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle)), []
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        return [], [f"Manifest could not be read for quality gate: {exc}"]


def _manifest_has_placeholders(rows: list[dict[str, str]]) -> bool:
    return any("<" in _clean(value) and ">" in _clean(value) for row in rows for value in row.values())


def _contains_demo_proxy_cache(row: dict[str, str]) -> bool:
    text = " ".join(_clean(value).lower() for value in row.values())
    return "demo" in text or "proxy" in text or "cache" in text


def _missing_manifest_fields(row: dict[str, str]) -> list[str]:
    return [field for field in USER_CURATED_MANIFEST_COLUMNS if not _clean(row.get(field))]


def _downgrade_to_expert_review(current_status: str) -> str:
    if current_status == NOT_READY_FOR_SCORING:
        return current_status
    return REQUIRES_EXPERT_REVIEW


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()
