from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .evolutionary_evidence_contract import EVOLUTIONARY_VARIABLES
from .evolutionary_fitness_cost_screening import (
    audit_screened_fitness_cost_literature,
)


COVERAGE_BINS: tuple[str, ...] = (
    "0_explicit_variables",
    "1_explicit_variable",
    "2_explicit_variables",
    "3_or_more_explicit_variables",
)

IDENTITY_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "protein_id",
    "gene",
    "taxon_id",
    "organism",
    "strain",
)

PROVENANCE_SUFFIXES: tuple[str, ...] = (
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

MISSINGNESS_REASON_PRIORITY: tuple[str, ...] = (
    "quantitative_evidence_available",
    "numeric_value_not_extractable",
    "literature_found_qualitative_only",
    "conflicting_results",
    "strain_context_mismatch",
    "experimental_condition_mismatch",
    "mutation_not_mappable_to_candidate",
    "source_mode_disallows_curated_evidence",
    "provider_failed",
    "contract_validation_failed",
    "no_experimental_literature_found",
    "literature_screening_not_documented_for_candidate",
    "evidence_not_contract_explicit",
)


def _norm(value: Any) -> str:
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.casefold() in {"", "nan", "none", "null", "<na>", "not_reported"}:
        return ""
    return text


def _norm_lower(value: Any) -> str:
    return _norm(value).casefold()


def _norm_taxon(value: Any) -> str:
    text = _norm(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if math.isfinite(number) and number.is_integer():
        return str(int(number))
    return text


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value is pd.NA:
        return False
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)):
                return False
        except (TypeError, ValueError):
            pass
        return bool(value)
    return _norm_lower(value) in {"1", "true", "yes", "y", "supported", "explicit"}


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _candidate_id(row: pd.Series) -> str:
    for column in (
        "candidate_id",
        "protein_id",
        "accession",
        "uniprot_accession",
        "entry",
        "locus_tag",
    ):
        value = _norm(row.get(column))
        if value:
            return value
    return ""


def _effective_mode(config: dict[str, Any]) -> str:
    online = config.get("online_sources", {}) if isinstance(config, dict) else {}
    return _norm_lower(
        online.get("source_mode_effective")
        or online.get("source_mode")
        or online.get("source_mode_default")
    ) or "not_reported"


def _thresholds(config: dict[str, Any]) -> tuple[int, int]:
    cfg = config.get("evolutionary_escape_risk", {}) if isinstance(config, dict) else {}
    minimum_variables = int(
        cfg.get("minimum_explicit_variables", cfg.get("minimum_available_variables", 3))
    )
    minimum_groups = int(cfg.get("minimum_independent_evidence_groups", 2))
    return minimum_variables, minimum_groups


def _diagnostic_reason(row: pd.Series, variable: str) -> str:
    if variable == "fitness_cost_of_escape":
        return _norm(row.get("fitness_cost_curated_evidence_reason"))
    if variable == "evolutionary_constraint_score":
        return _norm(row.get("bvbrc_evolutionary_evidence_reason"))
    if variable == "resistance_emergence_risk":
        return _norm(row.get("amrfinder_evolutionary_evidence_reason"))
    return ""


def _canonical_missingness_reason(
    row: pd.Series,
    variable: str,
    *,
    contract_explicit: bool,
    declared_explicit: bool,
    source_mode: str,
) -> tuple[str, str]:
    if contract_explicit:
        return "quantitative_evidence_available", "accepted_by_stage4a_contract"

    diagnostic = _diagnostic_reason(row, variable)
    diagnostic_lower = diagnostic.casefold()
    if variable == "fitness_cost_of_escape" and source_mode in {
        "online_strict",
        "online_only",
    }:
        return "source_mode_disallows_curated_evidence", diagnostic or source_mode
    if declared_explicit:
        return "contract_validation_failed", diagnostic or "declared_explicit_but_not_contract_explicit"
    if any(token in diagnostic_lower for token in ("provider_failed", "retrieval_not_usable", "api_failed")):
        return "provider_failed", diagnostic
    if any(token in diagnostic_lower for token in ("mapping", "taxon_mismatch", "gene_mismatch")):
        return "mutation_not_mappable_to_candidate", diagnostic
    if variable == "fitness_cost_of_escape":
        return (
            "literature_screening_not_documented_for_candidate",
            diagnostic or "no_stage4e_or_stage4f_candidate_record",
        )
    return "evidence_not_contract_explicit", diagnostic or "no_contract_explicit_record"


def _canonical_record(
    row: pd.Series,
    variable: str,
    *,
    source_mode: str,
) -> dict[str, Any]:
    candidate = _candidate_id(row)
    value = _finite_number(row.get(variable))
    contract_explicit = _as_bool(row.get(f"{variable}_contract_explicit"))
    declared_explicit = _as_bool(row.get(f"{variable}_is_explicit"))
    candidate_supported = _as_bool(row.get("evolutionary_evidence_contract_supported"))
    missingness_reason, missingness_detail = _canonical_missingness_reason(
        row,
        variable,
        contract_explicit=contract_explicit,
        declared_explicit=declared_explicit,
        source_mode=source_mode,
    )

    if contract_explicit:
        evidence_class = "explicit_quantitative"
    elif declared_explicit:
        evidence_class = "rejected_explicit"
    elif value is not None:
        evidence_class = "proxy_or_derived"
    else:
        evidence_class = "missing"

    record: dict[str, Any] = {
        "candidate_id": candidate,
        "protein_id": _norm(row.get("protein_id")) or candidate,
        "gene": _norm(row.get("gene")),
        "taxon_id": _norm_taxon(row.get("taxon_id")),
        "organism": _norm(row.get("organism")),
        "strain": _norm(row.get("strain")),
        "evolutionary_variable": variable,
        "evidence_record_id": f"canonical:{candidate}:{variable}",
        "record_scope": "canonical_scoring_input",
        "variable_value": value,
        "evidence_form": "quantitative" if value is not None else "none",
        "evidence_class": evidence_class,
        "qualitative_finding": "",
        "mutation": "",
        "assay_context": "",
        "is_proxy": bool(value is not None and not contract_explicit),
        "is_explicit_requested": declared_explicit,
        "contract_explicit": contract_explicit,
        "variable_scoring_eligible": contract_explicit,
        "candidate_supported_scoring_enabled": candidate_supported,
        "affects_proxy_scoring": value is not None,
        "affects_supported_scoring": bool(contract_explicit and candidate_supported),
        "coverage_mapping_status": _norm_lower(row.get(f"{variable}_mapping_status")) or "not_reported",
        "missingness_reason": missingness_reason,
        "missingness_detail": missingness_detail,
        "contract_errors": _norm(row.get("evolutionary_evidence_contract_errors")) or "none",
        "contract_warnings": _norm(row.get("evolutionary_evidence_contract_warnings")) or "none",
        "source_mode": source_mode,
    }
    for suffix in PROVENANCE_SUFFIXES:
        output_column = "evidence_taxon_id" if suffix == "taxon_id" else suffix
        value = row.get(f"{variable}_{suffix}")
        record[output_column] = _norm_taxon(value) if suffix == "taxon_id" else _norm(value)
    record["pmid"] = ""
    record["doi"] = ""
    return record


def _screening_missingness_reason(row: pd.Series) -> tuple[str, str]:
    status = _norm_lower(row.get("derived_screening_status") or row.get("screening_status"))
    reason = _norm(row.get("screening_reason")) or status
    if status in {"promoted_to_stage4e_catalog", "quantitative_candidate_not_promoted"}:
        return "quantitative_evidence_available", reason
    if "missing_numeric_relative_fitness" in status:
        return "numeric_value_not_extractable", reason
    if "non_direct_mapping" in status or "non_protein_candidate_scope" in status:
        return "mutation_not_mappable_to_candidate", reason
    if "incomplete_provenance" in status or status == "invalid_screening_schema":
        return "contract_validation_failed", reason
    if _norm(row.get("finding_direction")):
        return "literature_found_qualitative_only", reason
    return "literature_found_qualitative_only", reason


def _screening_record(
    row: pd.Series,
    *,
    candidate: pd.Series | None,
    mapping_status: str,
    source_mode: str,
) -> dict[str, Any]:
    missingness_reason, missingness_detail = _screening_missingness_reason(row)
    if mapping_status != "unique_gene_and_taxon":
        missingness_reason = "mutation_not_mappable_to_candidate"
        missingness_detail = mapping_status

    relative_fitness = _finite_number(row.get("relative_fitness"))
    finding = _norm(row.get("finding_direction"))
    candidate_id = _candidate_id(candidate) if candidate is not None else ""
    protein_id = _norm(candidate.get("protein_id")) if candidate is not None else ""
    evidence_form = "quantitative" if relative_fitness is not None else "qualitative" if finding else "none"
    evidence_class = _norm_lower(row.get("derived_screening_status")) or "screening_only"
    record_id_parts = [
        _norm(row.get("gene")),
        _norm(row.get("mutation")),
        _norm(row.get("source_record")),
        _norm(row.get("assay_context")),
    ]
    return {
        "candidate_id": candidate_id,
        "protein_id": protein_id or candidate_id,
        "gene": _norm(row.get("gene")),
        "taxon_id": _norm_taxon(row.get("taxon_id")),
        "organism": _norm(candidate.get("organism")) if candidate is not None else "",
        "strain": _norm(candidate.get("strain")) if candidate is not None else "",
        "evolutionary_variable": "fitness_cost_of_escape",
        "evidence_record_id": "screening:" + "|".join(record_id_parts),
        "record_scope": "screened_literature",
        "variable_value": relative_fitness,
        "evidence_form": evidence_form,
        "evidence_class": evidence_class,
        "qualitative_finding": finding,
        "mutation": _norm(row.get("mutation")),
        "assay_context": _norm(row.get("assay_context")),
        "is_proxy": False,
        "is_explicit_requested": False,
        "contract_explicit": False,
        "variable_scoring_eligible": False,
        "candidate_supported_scoring_enabled": (
            _as_bool(candidate.get("evolutionary_evidence_contract_supported"))
            if candidate is not None
            else False
        ),
        "affects_proxy_scoring": False,
        "affects_supported_scoring": False,
        "source_type": _norm(row.get("source_type")),
        "source_database": _norm(row.get("source_database")),
        "source_record": _norm(row.get("source_record")),
        "source_version": _norm(row.get("source_version")),
        "retrieved_at": _norm(row.get("retrieved_at")),
        "mapping_method": _norm(row.get("mapping_method")),
        "mapping_status": _norm(row.get("mapping_status")),
        "coverage_mapping_status": mapping_status,
        "evidence_status": _norm(row.get("evidence_status")),
        "evidence_confidence": _norm(row.get("evidence_confidence")),
        "independence_group": "",
        "method_scope": _norm(row.get("method_scope")),
        "notes": _norm(row.get("notes")),
        "evidence_taxon_id": _norm_taxon(row.get("taxon_id")),
        "pmid": _norm(row.get("pmid")),
        "doi": _norm(row.get("doi")),
        "missingness_reason": missingness_reason,
        "missingness_detail": missingness_detail,
        "contract_errors": "not_evaluated_for_stage4a",
        "contract_warnings": "screening_only_no_scoring_effect",
        "source_mode": source_mode,
    }


def resolve_screened_literature_to_candidates(
    features: pd.DataFrame,
    screening_summary: pd.DataFrame,
    *,
    source_mode: str,
) -> pd.DataFrame:
    """Map Stage 4F records without fanning ambiguous gene matches out to candidates."""

    if screening_summary.empty:
        return pd.DataFrame()

    candidates = features.copy()
    candidates["_coverage_gene"] = candidates.get(
        "gene", pd.Series([""] * len(candidates), index=candidates.index)
    ).map(_norm_lower)
    candidates["_coverage_taxon"] = candidates.get(
        "taxon_id", pd.Series([""] * len(candidates), index=candidates.index)
    ).map(_norm_taxon)

    rows: list[dict[str, Any]] = []
    for _, screened in screening_summary.iterrows():
        gene = _norm_lower(screened.get("gene"))
        taxon = _norm_taxon(screened.get("taxon_id"))
        matches = candidates[
            candidates["_coverage_gene"].eq(gene)
            & candidates["_coverage_taxon"].eq(taxon)
        ]
        if len(matches) == 1:
            rows.append(
                _screening_record(
                    screened,
                    candidate=matches.iloc[0],
                    mapping_status="unique_gene_and_taxon",
                    source_mode=source_mode,
                )
            )
        else:
            status = "unmapped_gene_and_taxon" if matches.empty else "ambiguous_gene_and_taxon"
            rows.append(
                _screening_record(
                    screened,
                    candidate=None,
                    mapping_status=status,
                    source_mode=source_mode,
                )
            )
    return pd.DataFrame(rows)


def build_evolutionary_evidence_records(
    features: pd.DataFrame,
    screening_summary: pd.DataFrame | None,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build the auditable long-form Stage 4G evidence table."""

    source_mode = _effective_mode(config)
    if source_mode in {"online_strict", "online_only"}:
        screening_summary = pd.DataFrame()
    records = [
        _canonical_record(row, variable, source_mode=source_mode)
        for _, row in features.iterrows()
        for variable in EVOLUTIONARY_VARIABLES
    ]
    canonical = pd.DataFrame(records)
    screening = resolve_screened_literature_to_candidates(
        features,
        screening_summary if screening_summary is not None else pd.DataFrame(),
        source_mode=source_mode,
    )
    if screening.empty:
        return canonical
    return pd.concat([canonical, screening], ignore_index=True, sort=False)


def _coverage_bin(count: int) -> str:
    if count <= 0:
        return COVERAGE_BINS[0]
    if count == 1:
        return COVERAGE_BINS[1]
    if count == 2:
        return COVERAGE_BINS[2]
    return COVERAGE_BINS[3]


def _preferred_reason(reasons: list[str]) -> str:
    normalized = {_norm_lower(reason) for reason in reasons if _norm(reason)}
    for reason in MISSINGNESS_REASON_PRIORITY:
        if reason in normalized:
            return reason
    return sorted(normalized)[0] if normalized else "evidence_not_contract_explicit"


def _semicolon(values: list[str] | set[str]) -> str:
    clean = sorted({_norm(value) for value in values if _norm(value)})
    return "; ".join(clean) or "none"


def build_candidate_evolutionary_coverage(
    features: pd.DataFrame,
    evidence_records: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Summarize distinct explicit variables per candidate without counting records."""

    minimum_variables, minimum_groups = _thresholds(config)
    output: list[dict[str, Any]] = []
    for _, candidate in features.iterrows():
        candidate_id = _candidate_id(candidate)
        subset = evidence_records[evidence_records["candidate_id"].astype(str).eq(candidate_id)]
        canonical = subset[subset["record_scope"].eq("canonical_scoring_input")]
        explicit_variables = set(
            canonical.loc[canonical["contract_explicit"].fillna(False).astype(bool), "evolutionary_variable"]
            .dropna()
            .astype(str)
        )
        proxy_variables = set(
            canonical.loc[canonical["is_proxy"].fillna(False).astype(bool), "evolutionary_variable"]
            .dropna()
            .astype(str)
        )
        quantitative_mask = subset["evidence_form"].eq("quantitative") & ~subset[
            "is_proxy"
        ].fillna(False).astype(bool)
        quantitative_variables = set(
            subset.loc[quantitative_mask, "evolutionary_variable"]
            .dropna()
            .astype(str)
        )
        qualitative_variables = set(
            subset.loc[subset["evidence_form"].eq("qualitative"), "evolutionary_variable"]
            .dropna()
            .astype(str)
        )
        missing_variables = set(EVOLUTIONARY_VARIABLES) - explicit_variables
        missingness_parts: list[str] = []
        for variable in EVOLUTIONARY_VARIABLES:
            variable_rows = subset[subset["evolutionary_variable"].eq(variable)]
            reasons = variable_rows["missingness_reason"].fillna("").astype(str).tolist()
            missingness_parts.append(f"{variable}={_preferred_reason(reasons)}")

        explicit_count = len(explicit_variables)
        reported_count = int(
            max(
                0,
                _finite_number(candidate.get("evolutionary_escape_risk_explicit_variable_count")) or 0,
            )
        )
        group_count = int(
            max(
                0,
                _finite_number(candidate.get("evolutionary_escape_risk_independent_evidence_group_count")) or 0,
            )
        )
        meets_variables = explicit_count >= minimum_variables
        meets_groups = group_count >= minimum_groups
        contract_supported = _as_bool(candidate.get("evolutionary_evidence_contract_supported"))
        if contract_supported:
            support_status = "supported_explicit"
        elif meets_variables and not meets_groups:
            support_status = "explicit_threshold_met_independence_failed"
        elif explicit_count:
            support_status = "partial_explicit_evidence"
        else:
            support_status = "proxy_only_or_missing"

        output.append(
            {
                "candidate_id": candidate_id,
                "protein_id": _norm(candidate.get("protein_id")) or candidate_id,
                "gene": _norm(candidate.get("gene")),
                "taxon_id": _norm_taxon(candidate.get("taxon_id")),
                "organism": _norm(candidate.get("organism")),
                "strain": _norm(candidate.get("strain")),
                "explicit_variable_count": explicit_count,
                "reported_explicit_variable_count": reported_count,
                "contract_count_consistent": explicit_count == reported_count,
                "explicit_variables": _semicolon(explicit_variables),
                "proxy_variable_count": len(proxy_variables),
                "proxy_variables": _semicolon(proxy_variables),
                "quantitative_evidence_variable_count": len(quantitative_variables),
                "quantitative_evidence_variables": _semicolon(quantitative_variables),
                "qualitative_evidence_variable_count": len(qualitative_variables),
                "qualitative_evidence_variables": _semicolon(qualitative_variables),
                "qualitative_evidence_record_count": int(subset["evidence_form"].eq("qualitative").sum()),
                "independent_evidence_group_count": group_count,
                "independence_groups": _norm(candidate.get("evolutionary_escape_risk_independence_groups")) or "none",
                "missing_variables": _semicolon(missing_variables),
                "missingness_by_variable": "; ".join(missingness_parts),
                "coverage_bin": _coverage_bin(explicit_count),
                "minimum_explicit_variables": minimum_variables,
                "minimum_independent_evidence_groups": minimum_groups,
                "meets_explicit_variable_threshold": meets_variables,
                "meets_independence_threshold": meets_groups,
                "evolutionary_evidence_contract_supported": contract_supported,
                "evolutionary_dimension_support_status": support_status,
                "evolutionary_escape_proxy_score": _finite_number(candidate.get("evolutionary_escape_proxy_score")),
                "evolutionary_escape_supported_score": _finite_number(
                    candidate.get("evolutionary_escape_supported_score")
                ),
                "evolutionary_escape_proxy_penalty_applied": _finite_number(
                    candidate.get("evolutionary_escape_proxy_penalty_applied")
                ),
                "evolutionary_escape_supported_penalty_applied": _finite_number(
                    candidate.get("evolutionary_escape_supported_penalty_applied")
                ),
                "source_mode": _effective_mode(config),
                "stage4g_scoring_effect": False,
            }
        )
    return pd.DataFrame(output)


def build_evolutionary_coverage_distribution(
    candidate_coverage: pd.DataFrame,
) -> pd.DataFrame:
    total = len(candidate_coverage)
    rows: list[dict[str, Any]] = []
    for coverage_bin in COVERAGE_BINS:
        subset = (
            candidate_coverage[candidate_coverage["coverage_bin"].eq(coverage_bin)]
            if "coverage_bin" in candidate_coverage.columns
            else candidate_coverage.iloc[0:0]
        )
        count = len(subset)
        supported = int(
            subset.get(
                "evolutionary_evidence_contract_supported",
                pd.Series([False] * count, index=subset.index),
            )
            .fillna(False)
            .astype(bool)
            .sum()
        )
        rows.append(
            {
                "coverage_bin": coverage_bin,
                "candidate_count": count,
                "candidate_fraction": (count / total) if total else 0.0,
                "contract_supported_candidate_count": supported,
                "contract_supported_fraction": (supported / count) if count else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _markdown_distribution(distribution: pd.DataFrame) -> str:
    lines = [
        "| Coverage bin | Candidates | Fraction | Contract supported |",
        "| --- | ---: | ---: | ---: |",
    ]
    for _, row in distribution.iterrows():
        lines.append(
            f"| `{row['coverage_bin']}` | {int(row['candidate_count'])} | "
            f"{float(row['candidate_fraction']):.1%} | "
            f"{int(row['contract_supported_candidate_count'])} |"
        )
    return "\n".join(lines)


def write_evolutionary_coverage_outputs(
    base_dir: Path,
    features: pd.DataFrame,
    config: dict[str, Any],
    *,
    screening_summary: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Write Stage 4G audit outputs without modifying candidate scores."""

    base_dir = Path(base_dir)
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    if screening_summary is None:
        screening_summary = audit_screened_fitness_cost_literature(base_dir, config)

    records = build_evolutionary_evidence_records(features, screening_summary, config)
    coverage = build_candidate_evolutionary_coverage(features, records, config)
    distribution = build_evolutionary_coverage_distribution(coverage)
    minimum_variables, minimum_groups = _thresholds(config)

    records_path = results_dir / "evolutionary_coverage_evidence_records.csv"
    coverage_path = results_dir / "evolutionary_coverage_by_candidate.csv"
    distribution_path = results_dir / "evolutionary_coverage_distribution.csv"
    manifest_path = results_dir / "evolutionary_coverage_manifest.json"
    report_path = results_dir / "evolutionary_coverage_report.md"
    records.to_csv(records_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    distribution.to_csv(distribution_path, index=False)

    manifest = {
        "stage": "4G",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "coverage_reported",
        "source_mode": _effective_mode(config),
        "candidate_count": int(len(coverage)),
        "evidence_record_count": int(len(records)),
        "screened_literature_record_count": int(
            records["record_scope"].eq("screened_literature").sum()
        ) if not records.empty else 0,
        "minimum_explicit_variables": minimum_variables,
        "minimum_independent_evidence_groups": minimum_groups,
        "explicit_threshold_candidate_count": int(
            coverage["meets_explicit_variable_threshold"].fillna(False).astype(bool).sum()
        ) if not coverage.empty else 0,
        "contract_supported_candidate_count": int(
            coverage["evolutionary_evidence_contract_supported"].fillna(False).astype(bool).sum()
        ) if not coverage.empty else 0,
        "scoring_effect": False,
        "scoring_formula_changed": False,
        "theory_weights_changed": False,
        "auto_promotion_enabled": False,
        "outputs": {
            "evidence_records": str(records_path),
            "candidate_coverage": str(coverage_path),
            "distribution": str(distribution_path),
            "report": str(report_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        "\n".join(
            [
                "# Stage 4G — Evolutionary evidence coverage",
                "",
                "This report separates contract-explicit quantitative evidence, "
                "proxy/derived values, and screening-only qualitative literature.",
                "It does not change scoring formulas, Functional Node Theory weights, candidate scores, or ranking.",
                "Missing evidence is not interpreted as low evolutionary risk.",
                "",
                "## Coverage distribution",
                "",
                _markdown_distribution(distribution),
                "",
                "## Support gate",
                "",
                f"- Minimum explicit variables: **{minimum_variables}**",
                f"- Minimum independent evidence groups: **{minimum_groups}**",
                f"- Candidates meeting the variable threshold: **{manifest['explicit_threshold_candidate_count']}**",
                "- Candidates supported by the complete contract: "
                f"**{manifest['contract_supported_candidate_count']}**",
                "",
                "A candidate can meet the variable-count threshold and still fail the complete "
                "contract when the evidence is not sufficiently independent.",
                "Stage 4F qualitative findings remain visible but never become numeric "
                "fitness-cost values automatically.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest
