"""Manual approval gate for future user-curated controlled scoring.

This module does not run scoring, does not run the pipeline, and does not
produce rankings. It only validates whether an explicit expert approval record
is sufficient for a future controlled scoring step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


APPROVED_STATUS = "approved_for_controlled_scoring"

BLOCKING_QUALITY_GATE_DECISIONS = {
    "not_ready_for_scoring",
}

NON_APPROVED_STATUSES = {
    "not_approved",
    "rejected_for_scoring",
    "requires_additional_curation",
}

PLACEHOLDER_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "pending",
    "todo",
    "tbd",
    "unknown",
    "placeholder",
    "replace_me",
    "example",
    "demo",
}

PROHIBITED_PRIMARY_EVIDENCE_MARKERS = {
    "demo",
    "proxy",
    "cache",
    "cached",
    "template",
    "example",
    "synthetic",
}

REQUIRED_ACKNOWLEDGEMENTS = {
    "scoring_is_not_biological_validation",
    "scoring_is_not_clinical_validation",
    "scoring_is_not_therapeutic_recommendation",
    "high_score_does_not_equal_high_confidence",
    "incomplete_evidence_does_not_equal_low_risk",
    "demo_proxy_cache_are_not_real_evidence",
    "expert_review_required_before_controlled_scoring",
}


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _is_placeholder(value: Any) -> bool:
    normalized = _normalize(value).lower()
    return normalized in PLACEHOLDER_VALUES


def _as_mapping(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    return record


def load_scoring_approval(path: str | Path) -> dict[str, Any]:
    """Load a manual approval record from JSON.

    YAML support is intentionally not required here to avoid adding optional
    dependencies. Approval records can be authored as JSON or loaded from
    dictionaries in tests and future GUI integrations.
    """

    approval_path = Path(path)
    with approval_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return _as_mapping(data)


def validate_scoring_approval(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a user-curated manual approval record conservatively."""

    record = _as_mapping(record)
    errors: list[str] = []
    warnings: list[str] = []

    required_text_fields = {
        "dataset_id": "dataset_id is required.",
        "organism": "organism is required.",
        "reviewer_name": "reviewer_name is required.",
        "reviewer_role": "reviewer_role is required.",
        "review_date": "review_date is required.",
        "approval_scope": "approval_scope is required.",
        "notes": "notes are required.",
    }

    for field, message in required_text_fields.items():
        value = record.get(field)
        if _is_placeholder(value):
            errors.append(message)
        elif _is_placeholder_marker(value):
            errors.append(f"{field} contains a placeholder-like value.")

    strain_or_lineage = record.get("strain_or_lineage")
    if _is_placeholder(strain_or_lineage):
        warnings.append(
            "strain_or_lineage is missing or unresolved; controlled scoring should remain conservative."
        )

    approval_status = _normalize(record.get("approval_status"))
    if approval_status != APPROVED_STATUS:
        errors.append(
            "approval_status must be approved_for_controlled_scoring."
        )

    if approval_status in NON_APPROVED_STATUSES:
        errors.append(f"approval_status explicitly blocks scoring: {approval_status}.")

    quality_gate_decision = _normalize(record.get("quality_gate_decision"))
    if _is_placeholder(quality_gate_decision):
        errors.append("quality_gate_decision is required.")

    if quality_gate_decision in BLOCKING_QUALITY_GATE_DECISIONS:
        errors.append(
            "quality_gate_decision blocks controlled scoring because the dataset is not ready."
        )

    provenance_summary = _normalize(record.get("provenance_summary")).lower()
    if _is_placeholder(provenance_summary):
        errors.append("provenance_summary is required.")

    primary_evidence_type = _normalize(record.get("primary_evidence_type")).lower()
    if _is_placeholder(primary_evidence_type):
        errors.append("primary_evidence_type is required.")

    if primary_evidence_type in PROHIBITED_PRIMARY_EVIDENCE_MARKERS:
        errors.append(
            "demo, proxy, cache, template or example data cannot be primary evidence."
        )

    if any(marker in provenance_summary for marker in PROHIBITED_PRIMARY_EVIDENCE_MARKERS):
        warnings.append(
            "provenance_summary mentions demo/proxy/cache/template/example; expert review must confirm these are not primary evidence."
        )

    acknowledgements = record.get("explicit_acknowledgements", {})
    if not isinstance(acknowledgements, dict):
        errors.append("explicit_acknowledgements must be a dictionary.")
        acknowledgements = {}

    missing_acknowledgements = sorted(
        key for key in REQUIRED_ACKNOWLEDGEMENTS if acknowledgements.get(key) is not True
    )

    for key in missing_acknowledgements:
        errors.append(f"required acknowledgement missing or false: {key}")

    return {
        "valid": not errors,
        "allows_controlled_scoring": not errors,
        "errors": errors,
        "warnings": warnings,
        "approval_status": approval_status,
        "quality_gate_decision": quality_gate_decision,
        "required_acknowledgements": sorted(REQUIRED_ACKNOWLEDGEMENTS),
        "missing_acknowledgements": missing_acknowledgements,
    }


def approval_allows_controlled_scoring(record: dict[str, Any]) -> bool:
    """Return True only when the approval record passes all blocking checks."""

    return bool(validate_scoring_approval(record)["allows_controlled_scoring"])


def summarize_scoring_approval(record: dict[str, Any]) -> str:
    """Create a conservative human-readable summary of the approval record."""

    validation = validate_scoring_approval(record)
    dataset_id = _normalize(record.get("dataset_id")) or "UNSPECIFIED_DATASET"
    organism = _normalize(record.get("organism")) or "UNSPECIFIED_ORGANISM"
    approval_status = validation["approval_status"] or "UNSPECIFIED_STATUS"
    quality_gate_decision = validation["quality_gate_decision"] or "UNSPECIFIED_GATE"

    lines = [
        f"Dataset: {dataset_id}",
        f"Organism: {organism}",
        f"Approval status: {approval_status}",
        f"Quality gate decision: {quality_gate_decision}",
        f"Allows controlled scoring: {validation['allows_controlled_scoring']}",
        "",
        "Interpretive limits:",
        "- This approval does not validate biology.",
        "- This approval does not validate clinical use.",
        "- This approval is not a therapeutic recommendation.",
        "- A future high therapeutic priority score must not be interpreted as high evidence confidence.",
        "- Incomplete evidence must not be interpreted as low risk.",
    ]

    if validation["errors"]:
        lines.append("")
        lines.append("Blocking errors:")
        lines.extend(f"- {error}" for error in validation["errors"])

    if validation["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in validation["warnings"])

    return "\n".join(lines)


def _is_placeholder_marker(value: Any) -> bool:
    normalized = _normalize(value).lower()
    return any(marker in normalized for marker in {"replace", "placeholder", "example"})

