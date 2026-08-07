from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


EVOLUTIONARY_VARIABLES: tuple[str, ...] = (
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
)

EXPLICIT_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "experimental",
        "literature_curated",
        "real_external",
        "real_external_online",
        "versioned_snapshot",
        "computed_from_real_data",
        "user_curated",
    }
)

NON_EXPLICIT_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "",
        "nan",
        "none",
        "missing",
        "not_reported",
        "unknown",
        "unresolved",
        "derived",
        "proxy",
        "proxy_inference",
        "proxy_hypothesis_only",
        "controlled",
        "controlled_provider",
        "default",
        "default_value",
        "demo",
        "demo_data",
        "template",
        "placeholder",
        "synthetic_fixture",
    }
)

EVALUABLE_EVIDENCE_STATUSES: frozenset[str] = frozenset(
    {"observed", "not_detected_with_method"}
)

NON_EVALUABLE_EVIDENCE_STATUSES: frozenset[str] = frozenset(
    {
        "missing_input",
        "insufficient_evidence",
        "unresolved",
        "provider_failed",
        "mapping_failed",
        "verified_empty_without_candidate_scope",
        "not_reported",
    }
)

DIRECT_MAPPING_STATUSES: frozenset[str] = frozenset(
    {
        "exact_accession",
        "exact_sequence_md5",
        "exact_locus_tag",
        "exact_gene_and_taxon",
    }
)

SUPPORTING_MAPPING_STATUSES: frozenset[str] = frozenset(
    {"family_match", "ortholog_match"}
)

NON_USABLE_MAPPING_STATUSES: frozenset[str] = frozenset(
    {
        "",
        "ambiguous",
        "unmapped",
        "unrelated_taxon",
        "mapping_failed",
        "not_applicable",
    }
)

CONFIDENCE_LEVELS: frozenset[str] = frozenset(
    {"low", "moderate", "high"}
)

REQUIRED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "source_database",
    "source_record",
    "source_version",
    "mapping_method",
    "independence_group",
)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none"}:
        return ""
    return text


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


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


@dataclass(frozen=True)
class EvolutionaryEvidenceRecord:
    candidate_id: str
    gene: str
    variable: str
    value: float | None
    source_type: str
    source_database: str
    source_record: str
    source_version: str
    retrieved_at: str
    mapping_method: str
    mapping_status: str
    evidence_status: str
    is_explicit: bool
    evidence_confidence: str
    independence_group: str
    method_scope: str = ""
    taxon_id: str = ""
    notes: str = ""

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
    ) -> "EvolutionaryEvidenceRecord":
        return cls(
            candidate_id=_norm(data.get("candidate_id")),
            gene=_norm(data.get("gene")),
            variable=_norm_lower(data.get("variable")),
            value=_finite_score(data.get("value")),
            source_type=_norm_lower(data.get("source_type")),
            source_database=_norm(data.get("source_database")),
            source_record=_norm(data.get("source_record")),
            source_version=_norm(data.get("source_version")),
            retrieved_at=_norm(data.get("retrieved_at")),
            mapping_method=_norm_lower(data.get("mapping_method")),
            mapping_status=_norm_lower(data.get("mapping_status")),
            evidence_status=_norm_lower(data.get("evidence_status")),
            is_explicit=bool(data.get("is_explicit", False)),
            evidence_confidence=_norm_lower(
                data.get("evidence_confidence")
            ),
            independence_group=_norm(data.get("independence_group")),
            method_scope=_norm(data.get("method_scope")),
            taxon_id=_norm(data.get("taxon_id")),
            notes=_norm(data.get("notes")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceValidation:
    record: EvolutionaryEvidenceRecord
    valid: bool
    eligible_as_explicit: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.record.to_dict(),
            "contract_valid": self.valid,
            "contract_explicit_eligible": self.eligible_as_explicit,
            "contract_errors": "; ".join(self.errors) or "none",
            "contract_warnings": "; ".join(self.warnings) or "none",
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_evidence_record(
    record: EvolutionaryEvidenceRecord | Mapping[str, Any],
    *,
    allow_supporting_mapping_as_explicit: bool = False,
) -> EvidenceValidation:
    item = (
        record
        if isinstance(record, EvolutionaryEvidenceRecord)
        else EvolutionaryEvidenceRecord.from_mapping(record)
    )
    errors: list[str] = []
    warnings: list[str] = []

    if not item.candidate_id:
        errors.append("missing_candidate_id")
    if item.variable not in EVOLUTIONARY_VARIABLES:
        errors.append("unsupported_variable")
    if item.value is None:
        errors.append("invalid_or_missing_value")
    if item.evidence_confidence not in CONFIDENCE_LEVELS:
        errors.append("invalid_evidence_confidence")
    if item.evidence_status not in (
        EVALUABLE_EVIDENCE_STATUSES
        | NON_EVALUABLE_EVIDENCE_STATUSES
    ):
        errors.append("unknown_evidence_status")
    if item.mapping_status not in (
        DIRECT_MAPPING_STATUSES
        | SUPPORTING_MAPPING_STATUSES
        | NON_USABLE_MAPPING_STATUSES
    ):
        errors.append("unknown_mapping_status")

    for field_name in REQUIRED_PROVENANCE_FIELDS:
        if not _norm(getattr(item, field_name)):
            errors.append(f"missing_{field_name}")

    if not item.retrieved_at:
        errors.append("missing_retrieved_at")

    source_is_explicit = item.source_type in EXPLICIT_SOURCE_TYPES
    if item.source_type in NON_EXPLICIT_SOURCE_TYPES:
        source_is_explicit = False
    elif item.source_type not in EXPLICIT_SOURCE_TYPES:
        warnings.append("unrecognized_source_type_not_explicit")
        source_is_explicit = False

    mapping_is_direct = item.mapping_status in DIRECT_MAPPING_STATUSES
    mapping_is_supporting = (
        item.mapping_status in SUPPORTING_MAPPING_STATUSES
    )
    mapping_eligible = mapping_is_direct or (
        allow_supporting_mapping_as_explicit and mapping_is_supporting
    )

    if mapping_is_supporting and not allow_supporting_mapping_as_explicit:
        warnings.append("supporting_mapping_not_direct_explicit_evidence")

    status_is_evaluable = (
        item.evidence_status in EVALUABLE_EVIDENCE_STATUSES
    )
    if (
        item.evidence_status == "not_detected_with_method"
        and not item.method_scope
    ):
        errors.append("not_detected_requires_method_scope")

    requested_explicit = bool(item.is_explicit)
    eligible = (
        not errors
        and requested_explicit
        and source_is_explicit
        and mapping_eligible
        and status_is_evaluable
    )

    if requested_explicit and not source_is_explicit:
        warnings.append("explicit_flag_rejected_by_source_type")
    if requested_explicit and not mapping_eligible:
        warnings.append("explicit_flag_rejected_by_mapping")
    if requested_explicit and not status_is_evaluable:
        warnings.append("explicit_flag_rejected_by_evidence_status")

    normalized = replace(item, is_explicit=eligible)
    return EvidenceValidation(
        record=normalized,
        valid=not errors,
        eligible_as_explicit=eligible,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def validate_evidence_records(
    records: Iterable[
        EvolutionaryEvidenceRecord | Mapping[str, Any]
    ],
    *,
    allow_supporting_mapping_as_explicit: bool = False,
) -> list[EvidenceValidation]:
    return [
        validate_evidence_record(
            record,
            allow_supporting_mapping_as_explicit=(
                allow_supporting_mapping_as_explicit
            ),
        )
        for record in records
    ]


def evidence_validations_to_frame(
    validations: Sequence[EvidenceValidation],
) -> pd.DataFrame:
    return pd.DataFrame([item.to_dict() for item in validations])


def summarize_candidate_evidence(
    validations: Sequence[EvidenceValidation],
    *,
    minimum_explicit_variables: int = 3,
    minimum_independent_groups: int = 2,
) -> pd.DataFrame:
    rows = [item.to_dict() for item in validations]
    if not rows:
        return pd.DataFrame(
            columns=[
                "candidate_id",
                "explicit_variable_count",
                "independent_evidence_group_count",
                "explicit_variables",
                "independence_groups",
                "supported_by_contract",
            ]
        )

    frame = pd.DataFrame(rows)
    candidates = sorted(frame["candidate_id"].dropna().astype(str).unique())
    output: list[dict[str, Any]] = []

    for candidate_id in candidates:
        subset = frame[frame["candidate_id"].astype(str) == candidate_id]
        eligible = subset[
            subset["contract_explicit_eligible"].fillna(False).astype(bool)
        ]
        variables = sorted(
            {
                str(value)
                for value in eligible["variable"].dropna()
                if str(value)
            }
        )
        groups = sorted(
            {
                str(value)
                for value in eligible["independence_group"].dropna()
                if str(value)
            }
        )
        output.append(
            {
                "candidate_id": candidate_id,
                "explicit_variable_count": len(variables),
                "independent_evidence_group_count": len(groups),
                "explicit_variables": "; ".join(variables) or "none",
                "independence_groups": "; ".join(groups) or "none",
                "supported_by_contract": (
                    len(variables) >= minimum_explicit_variables
                    and len(groups) >= minimum_independent_groups
                ),
            }
        )

    return pd.DataFrame(output)


def load_contract_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("The evolutionary evidence config must be an object.")
    return data
