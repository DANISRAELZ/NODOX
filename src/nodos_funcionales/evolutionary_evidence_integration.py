from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .evolutionary_evidence_contract import (
    EVOLUTIONARY_VARIABLES,
    EvidenceValidation,
    validate_evidence_records,
)


VARIABLE_ALIASES: dict[str, tuple[str, ...]] = {
    "mutation_tolerance_score": ("mutational_tolerance_score",),
}

CANDIDATE_ID_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "protein_id",
    "accession",
    "uniprot_accession",
    "entry",
    "locus_tag",
)

GENE_COLUMNS: tuple[str, ...] = (
    "gene",
    "gene_symbol",
    "locus_tag",
)

EVIDENCE_METADATA_SUFFIXES: tuple[str, ...] = (
    "source_type",
    "source_database",
    "source_record",
    "source_version",
    "retrieved_at",
    "mapping_method",
    "mapping_status",
    "evidence_status",
    "evidence_confidence",
    "independence_group",
    "method_scope",
    "taxon_id",
    "notes",
)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def _finite_score(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    if numeric < 0.0 or numeric > 1.0:
        return None
    return numeric


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)):
                return False
        except (TypeError, ValueError):
            pass
        return bool(value)
    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "explicit",
        "supported",
    }


def _first_text(row: pd.Series, columns: tuple[str, ...]) -> str:
    for column in columns:
        if column not in row.index:
            continue
        value = _norm(row.get(column))
        if value:
            return value
    return ""


def _variable_prefix(row: pd.Series, variable: str) -> str:
    if variable in row.index and _finite_score(row.get(variable)) is not None:
        return variable
    for alias in VARIABLE_ALIASES.get(variable, ()):
        if alias in row.index and _finite_score(row.get(alias)) is not None:
            return alias
    return variable


def _metadata_value(row: pd.Series, prefix: str, suffix: str) -> Any:
    column = f"{prefix}_{suffix}"
    if column in row.index:
        return row.get(column)
    return None


def _has_evidence_payload(row: pd.Series, prefix: str) -> bool:
    if _finite_score(row.get(prefix)) is not None:
        return True
    explicit_column = f"{prefix}_is_explicit"
    if explicit_column in row.index and _as_bool(row.get(explicit_column)):
        return True
    return any(
        _norm(_metadata_value(row, prefix, suffix))
        for suffix in EVIDENCE_METADATA_SUFFIXES
    )


def _build_record(
    row: pd.Series,
    variable: str,
) -> dict[str, Any] | None:
    prefix = _variable_prefix(row, variable)
    if not _has_evidence_payload(row, prefix):
        return None

    taxon_id = _metadata_value(row, prefix, "taxon_id")
    if not _norm(taxon_id) and "taxon_id" in row.index:
        taxon_id = row.get("taxon_id")

    return {
        "candidate_id": _first_text(row, CANDIDATE_ID_COLUMNS),
        "gene": _first_text(row, GENE_COLUMNS),
        "variable": variable,
        "value": row.get(prefix),
        "source_type": _metadata_value(row, prefix, "source_type"),
        "source_database": _metadata_value(row, prefix, "source_database"),
        "source_record": _metadata_value(row, prefix, "source_record"),
        "source_version": _metadata_value(row, prefix, "source_version"),
        "retrieved_at": _metadata_value(row, prefix, "retrieved_at"),
        "mapping_method": _metadata_value(row, prefix, "mapping_method"),
        "mapping_status": _metadata_value(row, prefix, "mapping_status"),
        "evidence_status": _metadata_value(row, prefix, "evidence_status"),
        "is_explicit": _as_bool(row.get(f"{prefix}_is_explicit")),
        "evidence_confidence": _metadata_value(
            row,
            prefix,
            "evidence_confidence",
        ),
        "independence_group": _metadata_value(
            row,
            prefix,
            "independence_group",
        ),
        "method_scope": _metadata_value(row, prefix, "method_scope"),
        "taxon_id": taxon_id,
        "notes": _metadata_value(row, prefix, "notes"),
    }


def _join_messages(
    validations: list[EvidenceValidation],
    attribute: str,
) -> str:
    messages: list[str] = []
    for validation in validations:
        for message in getattr(validation, attribute):
            tagged = f"{validation.record.variable}:{message}"
            if tagged not in messages:
                messages.append(tagged)
    return "; ".join(messages) or "none"


def summarize_feature_frame_evidence(
    frame: pd.DataFrame,
    *,
    minimum_explicit_variables: int = 3,
    minimum_independent_groups: int = 2,
    allow_supporting_mapping_as_explicit: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate flattened per-variable evidence metadata for scoring.

    The adapter deliberately does not infer explicit evidence from numeric values,
    source labels, or legacy flags alone. A variable is contract-explicit only
    when the Stage 4A record validator accepts its provenance, mapping, evidence
    status and requested explicit flag.

    Returns a row-aligned contract summary and a boolean matrix indicating which
    evolutionary variables are eligible as explicit evidence.
    """

    summary_rows: list[dict[str, Any]] = []
    explicit_matrix = pd.DataFrame(
        False,
        index=frame.index,
        columns=list(EVOLUTIONARY_VARIABLES),
        dtype=bool,
    )

    for index, row in frame.iterrows():
        records = [
            record
            for variable in EVOLUTIONARY_VARIABLES
            if (record := _build_record(row, variable)) is not None
        ]
        validations = validate_evidence_records(
            records,
            allow_supporting_mapping_as_explicit=(
                allow_supporting_mapping_as_explicit
            ),
        )
        eligible = [
            validation
            for validation in validations
            if validation.eligible_as_explicit
        ]

        variables = sorted(
            {validation.record.variable for validation in eligible}
        )
        groups = sorted(
            {
                validation.record.independence_group
                for validation in eligible
                if validation.record.independence_group
            }
        )

        for variable in variables:
            explicit_matrix.at[index, variable] = True

        requested_explicit = sum(
            1 for validation in validations if validation.record.is_explicit
        )
        valid_records = sum(1 for validation in validations if validation.valid)
        supported = (
            len(variables) >= int(minimum_explicit_variables)
            and len(groups) >= int(minimum_independent_groups)
        )
        summary_rows.append(
            {
                "explicit_variable_count": len(variables),
                "independent_evidence_group_count": len(groups),
                "explicit_variables": "; ".join(variables) or "none",
                "independence_groups": "; ".join(groups) or "none",
                "supported_by_contract": supported,
                "contract_record_count": len(validations),
                "contract_valid_record_count": valid_records,
                "contract_explicit_record_count": len(eligible),
                "contract_rejected_explicit_record_count": max(
                    0,
                    requested_explicit - len(eligible),
                ),
                "contract_errors": _join_messages(validations, "errors"),
                "contract_warnings": _join_messages(validations, "warnings"),
            }
        )

    summary = pd.DataFrame(summary_rows, index=frame.index)
    if summary.empty:
        summary = pd.DataFrame(
            index=frame.index,
            columns=[
                "explicit_variable_count",
                "independent_evidence_group_count",
                "explicit_variables",
                "independence_groups",
                "supported_by_contract",
                "contract_record_count",
                "contract_valid_record_count",
                "contract_explicit_record_count",
                "contract_rejected_explicit_record_count",
                "contract_errors",
                "contract_warnings",
            ],
        )
    return summary, explicit_matrix
