from __future__ import annotations

from pathlib import Path

import pandas as pd


USER_CURATED_CONSERVATION_REQUIRED_COLUMNS = [
    "organism",
    "strain",
    "protein_id",
    "gene",
    "conservation_scope",
    "core_genome_presence",
    "strain_coverage_score",
    "allelic_conservation",
    "variant_burden",
    "source_database",
    "evidence_status",
    "curator_notes",
]

STRAIN_CONSERVATION_TEMPLATE_COLUMNS = [
    "protein_id",
    "gene",
    "core_genome_presence",
    "strain_coverage_score",
    "allelic_conservation",
    "variant_burden",
    "database",
]

USER_CURATED_MANUAL_CURATION_REQUIRED_COLUMNS = [
    "organism",
    "strain",
    "protein_id",
    "gene",
    "curator_name",
    "curation_date",
    "curation_decision",
    "evidence_summary",
    "evidence_status",
    "source_database",
    "reference_or_note",
    "curator_notes",
]

EVIDENCE_QUALITY_TEMPLATE_COLUMNS = [
    "protein_id",
    "gene",
    "evidence_quality_score",
    "confidence_ceiling",
    "evidence_source_type",
    "evidence_notes",
    "audit_flags",
    "phase3_notes",
    "database",
]


def transform_user_curated_conservation_to_strain_conservation(input_path: str | Path) -> pd.DataFrame:
    """Transform a user-curated conservation CSV into strain_conservation shape.

    The transformation is deliberately conservative: it preserves observed
    conservation values and traceability metadata, but does not compute scores,
    infer risk, import a layer, or write files.
    """
    source = Path(input_path)
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    _validate_user_curated_conservation_columns(df.columns)

    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "protein_id": _clean(row["protein_id"]),
                "gene": _clean(row["gene"]),
                "core_genome_presence": _normalize_core_genome_presence(row["core_genome_presence"]),
                "strain_coverage_score": _clean(row["strain_coverage_score"]),
                "allelic_conservation": _clean(row["allelic_conservation"]),
                "variant_burden": _clean(row["variant_burden"]),
                "database": _build_traceable_database_field(row),
            }
        )

    return pd.DataFrame(rows, columns=STRAIN_CONSERVATION_TEMPLATE_COLUMNS)


def transform_user_curated_manual_curation_to_evidence_quality(input_path: str | Path) -> pd.DataFrame:
    """Transform manual user curation into evidence_quality shape.

    The numeric evidence fields are conservative ceilings for interpretability
    only. They are not therapeutic ranking values and never promote pending
    manual review to strong evidence.
    """
    source = Path(input_path)
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    _validate_user_curated_manual_curation_columns(df.columns)

    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        evidence_value = _manual_curation_evidence_value(row["evidence_status"])
        rows.append(
            {
                "protein_id": _clean(row["protein_id"]),
                "gene": _clean(row["gene"]),
                "evidence_quality_score": evidence_value,
                "confidence_ceiling": evidence_value,
                "evidence_source_type": "user_curated_manual_curation",
                "evidence_notes": _build_manual_curation_evidence_notes(row),
                "audit_flags": _build_manual_curation_audit_flags(row),
                "phase3_notes": "manual_curation_interpretive_only; no_clinical_recommendation",
                "database": _build_manual_curation_database_field(row),
            }
        )

    return pd.DataFrame(rows, columns=EVIDENCE_QUALITY_TEMPLATE_COLUMNS)


def _validate_user_curated_conservation_columns(columns: pd.Index) -> None:
    present = {str(column) for column in columns}
    missing = [column for column in USER_CURATED_CONSERVATION_REQUIRED_COLUMNS if column not in present]
    if missing:
        raise ValueError(
            "user_curated conservation CSV is missing required columns: "
            + ", ".join(missing)
        )


def _validate_user_curated_manual_curation_columns(columns: pd.Index) -> None:
    present = {str(column) for column in columns}
    missing = [column for column in USER_CURATED_MANUAL_CURATION_REQUIRED_COLUMNS if column not in present]
    if missing:
        raise ValueError(
            "user_curated manual curation CSV is missing required columns: "
            + ", ".join(missing)
        )


def _normalize_core_genome_presence(value: object) -> str:
    cleaned = _clean(value)
    lowered = cleaned.casefold()
    if lowered in {"true", "yes", "y"}:
        return "1"
    if lowered in {"false", "no", "n"}:
        return "0"
    return cleaned


def _manual_curation_evidence_value(evidence_status: object) -> str:
    lowered = _clean(evidence_status).casefold()
    if lowered in {"reviewed", "curated_reviewed"}:
        return "0.40"
    return "0.20"


def _build_traceable_database_field(row: pd.Series) -> str:
    metadata = [
        ("source_database", row["source_database"]),
        ("source_type", "user_curated"),
        ("organism", row["organism"]),
        ("strain", row["strain"]),
        ("conservation_scope", row["conservation_scope"]),
        ("evidence_status", row["evidence_status"]),
        ("curator_notes", row["curator_notes"]),
    ]
    return "; ".join(f"{key}={_clean(value)}" for key, value in metadata)


def _build_manual_curation_evidence_notes(row: pd.Series) -> str:
    metadata = [
        ("evidence_summary", row["evidence_summary"]),
        ("evidence_status", row["evidence_status"]),
        ("curation_decision", row["curation_decision"]),
        ("reference_or_note", row["reference_or_note"]),
        ("curator_notes", row["curator_notes"]),
    ]
    return "; ".join(f"{key}={_clean(value)}" for key, value in metadata)


def _build_manual_curation_audit_flags(row: pd.Series) -> str:
    flags = ["user_curated", "manual_curation", "interpretive_only"]
    status = _clean(row["evidence_status"]).casefold()
    decision = _clean(row["curation_decision"]).casefold()
    reference = _clean(row["reference_or_note"]).casefold()
    if status in {"pending_review", "limited", "insufficient", "insufficient_evidence"}:
        flags.append("limited_confidence")
    if decision == "include_for_structure_check":
        flags.append("not_experimental_validation")
    if "local" in reference and "doi" not in reference:
        flags.append("local_note_not_verified_literature")
    return ";".join(flags)


def _build_manual_curation_database_field(row: pd.Series) -> str:
    metadata = [
        ("source_database", row["source_database"]),
        ("source_type", "user_curated"),
        ("organism", row["organism"]),
        ("strain", row["strain"]),
        ("curator_name", row["curator_name"]),
        ("curation_date", row["curation_date"]),
    ]
    return "; ".join(f"{key}={_clean(value)}" for key, value in metadata)


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()
