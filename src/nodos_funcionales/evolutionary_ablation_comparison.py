from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


IDENTITY_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "protein_id",
    "accession",
    "entry",
    "gene",
    "locus_tag",
)

REQUIRED_ABLATION_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "ranking_without_evolutionary_information_score",
    "ranking_without_evolutionary_information_rank",
    "ranking_with_proxy_evolutionary_score",
    "ranking_with_proxy_evolutionary_rank",
    "ranking_with_supported_evolutionary_score",
    "ranking_with_supported_evolutionary_rank",
    "ranking_with_matched_proxy_evolutionary_score",
    "ranking_with_matched_proxy_evolutionary_rank",
    "supported_evolutionary_dimension_applied",
    "evolutionary_evidence_contract_supported",
)

COMPARISON_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "protein_id",
    "accession",
    "entry",
    "gene",
    "locus_tag",
    "explicit_variable_count",
    "explicit_variables",
    "proxy_variable_count",
    "proxy_variables",
    "quantitative_evidence_variable_count",
    "qualitative_evidence_variable_count",
    "qualitative_evidence_record_count",
    "independent_evidence_group_count",
    "independence_groups",
    "missing_variables",
    "missingness_by_variable",
    "coverage_bin",
    "source_mode",
    "evolutionary_dimension_support_status",
    "evolutionary_evidence_contract_supported",
    "contract_state_consistent",
    "contract_count_consistent",
    "supported_effect_evaluable",
    "supported_effect_status",
    "no_evolution_score",
    "no_evolution_rank",
    "proxy_operational_score",
    "proxy_operational_rank",
    "supported_operational_score",
    "supported_operational_rank",
    "proxy_matched_global_score",
    "proxy_matched_global_rank",
    "proxy_operational_score_delta_vs_no_evolution",
    "proxy_operational_rank_shift_vs_no_evolution",
    "supported_operational_global_score_delta_vs_no_evolution",
    "supported_operational_global_rank_shift_vs_no_evolution",
    "supported_global_rank_effect_attribution",
    "proxy_matched_score",
    "supported_matched_score",
    "proxy_matched_score_delta_vs_no_evolution",
    "supported_matched_score_delta_vs_no_evolution",
    "supported_minus_proxy_matched_score",
    "supported_subcohort_no_evolution_rank",
    "supported_subcohort_proxy_matched_rank",
    "supported_subcohort_supported_matched_rank",
    "paired_rank_comparison_evaluable",
    "stage4h_scoring_effect",
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
    return "" if text.casefold() in {"", "nan", "none", "null", "<na>"} else text


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value).casefold() in {"1", "true", "yes", "y", "supported"}


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].map(_as_bool).astype(bool)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(math.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _finite(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.notna() & numeric.map(lambda value: math.isfinite(float(value)))


def _normalized_ids(frame: pd.DataFrame) -> pd.Series:
    if "candidate_id" not in frame.columns:
        return pd.Series("", index=frame.index, dtype="string")
    return frame["candidate_id"].map(_norm).astype("string")


def build_ablation_coverage_mapping_audit(
    candidate_ablation: pd.DataFrame,
    candidate_coverage: pd.DataFrame,
) -> pd.DataFrame:
    """Audit the exact candidate-id join; gene fallback is intentionally forbidden."""

    left_ids = _normalized_ids(candidate_ablation)
    right_ids = _normalized_ids(candidate_coverage)
    left_counts = left_ids[left_ids.ne("")].value_counts().to_dict()
    right_counts = right_ids[right_ids.ne("")].value_counts().to_dict()
    rows: list[dict[str, Any]] = []
    for candidate_id in sorted(set(left_counts) | set(right_counts)):
        left_count = int(left_counts.get(candidate_id, 0))
        right_count = int(right_counts.get(candidate_id, 0))
        if left_count > 1:
            status = "duplicate_ablation_candidate_id"
        elif right_count > 1:
            status = "duplicate_coverage_candidate_id"
        elif left_count == 0:
            status = "missing_in_ablation"
        elif right_count == 0:
            status = "missing_in_stage4g_coverage"
        else:
            status = "exact_candidate_id"
        rows.append(
            {
                "candidate_id": candidate_id,
                "ablation_row_count": left_count,
                "coverage_row_count": right_count,
                "mapping_status": status,
                "analysis_eligible": status == "exact_candidate_id",
            }
        )
    for source, ids in (("ablation", left_ids), ("coverage", right_ids)):
        for index in ids[ids.eq("")].index:
            rows.append(
                {
                    "candidate_id": f"missing_candidate_id:{source}:{index}",
                    "ablation_row_count": int(source == "ablation"),
                    "coverage_row_count": int(source == "coverage"),
                    "mapping_status": f"missing_candidate_id_in_{source}",
                    "analysis_eligible": False,
                }
            )
    return pd.DataFrame(
        rows,
        columns=(
            "candidate_id",
            "ablation_row_count",
            "coverage_row_count",
            "mapping_status",
            "analysis_eligible",
        ),
    )


def _deterministic_rank(scores: pd.Series, ids: pd.Series) -> pd.Series:
    working = pd.DataFrame(
        {"score": pd.to_numeric(scores, errors="coerce"), "candidate_id": ids.astype(str)},
        index=scores.index,
    )
    ordered = working.sort_values(
        ["score", "candidate_id"],
        ascending=[False, True],
        kind="mergesort",
    )
    result = pd.Series(index=scores.index, dtype="Int64")
    result.loc[ordered.index] = range(1, len(ordered) + 1)
    return result


def _coverage_for_join(candidate_coverage: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "candidate_id",
        "explicit_variable_count",
        "reported_explicit_variable_count",
        "contract_count_consistent",
        "explicit_variables",
        "proxy_variable_count",
        "proxy_variables",
        "quantitative_evidence_variable_count",
        "qualitative_evidence_variable_count",
        "qualitative_evidence_record_count",
        "independent_evidence_group_count",
        "independence_groups",
        "missing_variables",
        "missingness_by_variable",
        "coverage_bin",
        "minimum_explicit_variables",
        "minimum_independent_evidence_groups",
        "meets_explicit_variable_threshold",
        "meets_independence_threshold",
        "evolutionary_evidence_contract_supported",
        "evolutionary_dimension_support_status",
        "source_mode",
    ]
    selected = candidate_coverage.reindex(columns=columns).copy()
    selected["candidate_id"] = _normalized_ids(selected)
    return selected.rename(
        columns={
            "evolutionary_evidence_contract_supported": "coverage_contract_supported",
            "contract_count_consistent": "coverage_contract_count_consistent",
        }
    )


def _support_reason(row: pd.Series, baseline_valid: bool) -> str:
    if not baseline_valid:
        return "not_evaluable_baseline_reconstruction_failed"
    if not bool(row.get("coverage_contract_count_consistent", False)):
        return "not_evaluable_contract_count_mismatch"
    if not bool(row.get("contract_state_consistent", False)):
        return "not_evaluable_contract_state_mismatch"
    explicit = int(row.get("explicit_variable_count", 0) or 0)
    groups = int(row.get("independent_evidence_group_count", 0) or 0)
    minimum_variables = int(row.get("minimum_explicit_variables", 3) or 3)
    minimum_groups = int(row.get("minimum_independent_evidence_groups", 2) or 2)
    if explicit == 0:
        return "not_evaluable_no_contract_explicit_evidence"
    if explicit < minimum_variables:
        return "not_evaluable_insufficient_explicit_variables"
    if groups < minimum_groups:
        return "not_evaluable_insufficient_independent_evidence"
    if not bool(row.get("coverage_contract_supported", False)):
        return "not_evaluable_contract_not_supported"
    if not bool(row.get("supported_evolutionary_dimension_applied", False)):
        return "not_evaluable_supported_dimension_not_applied"
    for column in (
        "ranking_without_evolutionary_information_score",
        "ranking_with_matched_proxy_evolutionary_score",
        "ranking_with_supported_evolutionary_score",
    ):
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.isna(value) or not math.isfinite(float(value)):
            return "not_evaluable_nonfinite_comparison_score"
    return "evaluable_contract_supported"


def build_evolutionary_ablation_comparison(
    candidate_ablation: pd.DataFrame,
    candidate_coverage: pd.DataFrame,
    ablation_summary: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build Stage 4H comparisons without modifying any production score."""

    mapping = build_ablation_coverage_mapping_audit(candidate_ablation, candidate_coverage)
    mapping_valid = bool(
        not mapping.empty
        and mapping["analysis_eligible"].fillna(False).astype(bool).all()
    )
    missing_columns = sorted(set(REQUIRED_ABLATION_COLUMNS) - set(candidate_ablation.columns))
    baseline_valid = bool(ablation_summary.get("baseline_reconstruction_valid", False))
    input_valid = mapping_valid and not missing_columns

    if not input_valid:
        status = "blocked_missing_required_ablation_columns" if missing_columns else "blocked_candidate_mapping"
        return (
            pd.DataFrame(columns=COMPARISON_COLUMNS),
            mapping,
            {
                "analysis_status": status,
                "mapping_valid": mapping_valid,
                "baseline_reconstruction_valid": baseline_valid,
                "missing_required_ablation_columns": missing_columns,
                "supported_evaluable_candidate_count": 0,
                "summary_rows": [],
            },
        )

    left = candidate_ablation.copy()
    left["candidate_id"] = _normalized_ids(left)
    joined = left.merge(
        _coverage_for_join(candidate_coverage),
        on="candidate_id",
        how="inner",
        validate="one_to_one",
    )
    ablation_contract = _bool_series(joined, "evolutionary_evidence_contract_supported")
    coverage_contract = _bool_series(joined, "coverage_contract_supported")
    joined["contract_state_consistent"] = ablation_contract.eq(coverage_contract)
    joined["coverage_contract_supported"] = coverage_contract
    joined["coverage_contract_count_consistent"] = _bool_series(
        joined, "coverage_contract_count_consistent"
    )
    joined["supported_evolutionary_dimension_applied"] = _bool_series(
        joined, "supported_evolutionary_dimension_applied"
    )
    for column, default in (
        ("explicit_variable_count", 0),
        ("independent_evidence_group_count", 0),
        ("minimum_explicit_variables", 3),
        ("minimum_independent_evidence_groups", 2),
    ):
        joined[column] = pd.to_numeric(joined[column], errors="coerce").fillna(default).astype(int)
    joined["supported_effect_status"] = joined.apply(
        lambda row: _support_reason(row, baseline_valid), axis=1
    )
    eligible = joined["supported_effect_status"].eq("evaluable_contract_supported")
    joined["supported_effect_evaluable"] = eligible

    output = pd.DataFrame(index=joined.index)
    for column in IDENTITY_COLUMNS:
        output[column] = joined[column] if column in joined.columns else ""
    passthrough = (
        "explicit_variable_count",
        "explicit_variables",
        "proxy_variable_count",
        "proxy_variables",
        "quantitative_evidence_variable_count",
        "qualitative_evidence_variable_count",
        "qualitative_evidence_record_count",
        "independent_evidence_group_count",
        "independence_groups",
        "missing_variables",
        "missingness_by_variable",
        "coverage_bin",
        "source_mode",
        "evolutionary_dimension_support_status",
    )
    for column in passthrough:
        output[column] = joined[column]
    output["evolutionary_evidence_contract_supported"] = coverage_contract
    output["contract_state_consistent"] = joined["contract_state_consistent"]
    output["contract_count_consistent"] = joined["coverage_contract_count_consistent"]
    output["supported_effect_evaluable"] = eligible
    output["supported_effect_status"] = joined["supported_effect_status"]

    score_mapping = {
        "no_evolution_score": "ranking_without_evolutionary_information_score",
        "no_evolution_rank": "ranking_without_evolutionary_information_rank",
        "proxy_operational_score": "ranking_with_proxy_evolutionary_score",
        "proxy_operational_rank": "ranking_with_proxy_evolutionary_rank",
        "supported_operational_score": "ranking_with_supported_evolutionary_score",
        "supported_operational_rank": "ranking_with_supported_evolutionary_rank",
        "proxy_matched_global_score": "ranking_with_matched_proxy_evolutionary_score",
        "proxy_matched_global_rank": "ranking_with_matched_proxy_evolutionary_rank",
    }
    for destination, source in score_mapping.items():
        output[destination] = _numeric(joined, source)

    output["proxy_operational_score_delta_vs_no_evolution"] = (
        output["proxy_operational_score"] - output["no_evolution_score"]
    )
    output["proxy_operational_rank_shift_vs_no_evolution"] = (
        output["proxy_operational_rank"] - output["no_evolution_rank"]
    )
    output["supported_operational_global_score_delta_vs_no_evolution"] = (
        output["supported_operational_score"] - output["no_evolution_score"]
    )
    output["supported_operational_global_rank_shift_vs_no_evolution"] = (
        output["supported_operational_rank"] - output["no_evolution_rank"]
    )
    global_shift = output["supported_operational_global_rank_shift_vs_no_evolution"]
    output["supported_global_rank_effect_attribution"] = [
        "direct_supported_and_cohort_effect"
        if is_eligible and shift != 0
        else "eligible_no_global_rank_change"
        if is_eligible
        else "indirect_cohort_rank_shift"
        if shift != 0
        else "not_evaluable_no_rank_change"
        for is_eligible, shift in zip(eligible, global_shift)
    ]

    output["proxy_matched_score"] = output["proxy_matched_global_score"].where(eligible)
    output["supported_matched_score"] = output["supported_operational_score"].where(eligible)
    output["proxy_matched_score_delta_vs_no_evolution"] = (
        output["proxy_matched_score"] - output["no_evolution_score"].where(eligible)
    )
    output["supported_matched_score_delta_vs_no_evolution"] = (
        output["supported_matched_score"] - output["no_evolution_score"].where(eligible)
    )
    output["supported_minus_proxy_matched_score"] = (
        output["supported_matched_score"] - output["proxy_matched_score"]
    )
    for column in (
        "supported_subcohort_no_evolution_rank",
        "supported_subcohort_proxy_matched_rank",
        "supported_subcohort_supported_matched_rank",
    ):
        output[column] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    eligible_index = output.index[eligible]
    if len(eligible_index):
        ids = output.loc[eligible_index, "candidate_id"].astype(str)
        output.loc[eligible_index, "supported_subcohort_no_evolution_rank"] = _deterministic_rank(
            output.loc[eligible_index, "no_evolution_score"], ids
        )
        output.loc[eligible_index, "supported_subcohort_proxy_matched_rank"] = _deterministic_rank(
            output.loc[eligible_index, "proxy_matched_score"], ids
        )
        output.loc[eligible_index, "supported_subcohort_supported_matched_rank"] = _deterministic_rank(
            output.loc[eligible_index, "supported_matched_score"], ids
        )
    output["paired_rank_comparison_evaluable"] = bool(len(eligible_index) >= 2) & eligible
    output["stage4h_scoring_effect"] = False

    summary_rows = build_ablation_comparison_summary(output, baseline_valid=baseline_valid)
    if not baseline_valid:
        analysis_status = "blocked_baseline_reconstruction"
    elif not len(eligible_index):
        analysis_status = "not_evaluable_no_supported_candidates"
    else:
        analysis_status = "comparison_evaluable"
    metadata = {
        "analysis_status": analysis_status,
        "mapping_valid": True,
        "baseline_reconstruction_valid": baseline_valid,
        "missing_required_ablation_columns": [],
        "candidate_count": int(len(output)),
        "supported_evaluable_candidate_count": int(eligible.sum()),
        "paired_rank_comparison_evaluable": bool(len(eligible_index) >= 2),
        "summary_rows": summary_rows.to_dict(orient="records"),
    }
    return output.reindex(columns=COMPARISON_COLUMNS), mapping, metadata


def _comparison_summary_row(
    comparison: pd.DataFrame,
    *,
    comparison_id: str,
    cohort: str,
    reference_score: str,
    comparison_score: str,
    reference_rank: str,
    comparison_rank: str,
    score_evaluable: bool,
    rank_evaluable: bool,
) -> dict[str, Any]:
    count = int(len(comparison))
    if not score_evaluable or count == 0:
        return {
            "comparison_id": comparison_id,
            "cohort": cohort,
            "evaluation_status": "not_evaluable",
            "candidate_count": count,
            "mean_score_delta": None,
            "median_score_delta": None,
            "mean_absolute_score_delta": None,
            "maximum_absolute_score_delta": None,
            "promoted_count": None,
            "demoted_count": None,
            "unchanged_count": None,
            "rank_correlation": None,
            "top_k": None,
            "top_k_overlap_count": None,
            "top_k_jaccard": None,
        }
    delta = _numeric(comparison, comparison_score) - _numeric(comparison, reference_score)
    rank_shift = _numeric(comparison, comparison_rank) - _numeric(comparison, reference_rank)
    top_k = min(10, count) if rank_evaluable else None
    reference_top = (
        set(comparison.nsmallest(top_k, reference_rank)["candidate_id"].astype(str))
        if top_k is not None
        else set()
    )
    comparison_top = (
        set(comparison.nsmallest(top_k, comparison_rank)["candidate_id"].astype(str))
        if top_k is not None
        else set()
    )
    union = reference_top | comparison_top
    rank_correlation = (
        float(_numeric(comparison, reference_rank).corr(_numeric(comparison, comparison_rank)))
        if rank_evaluable
        else None
    )
    return {
        "comparison_id": comparison_id,
        "cohort": cohort,
        "evaluation_status": "evaluable" if rank_evaluable else "score_only_rank_not_evaluable",
        "candidate_count": count,
        "mean_score_delta": float(delta.mean()),
        "median_score_delta": float(delta.median()),
        "mean_absolute_score_delta": float(delta.abs().mean()),
        "maximum_absolute_score_delta": float(delta.abs().max()),
        "promoted_count": int((rank_shift < 0).sum()) if rank_evaluable else None,
        "demoted_count": int((rank_shift > 0).sum()) if rank_evaluable else None,
        "unchanged_count": int((rank_shift == 0).sum()) if rank_evaluable else None,
        "rank_correlation": rank_correlation,
        "top_k": top_k,
        "top_k_overlap_count": len(reference_top & comparison_top) if rank_evaluable else None,
        "top_k_jaccard": (
            len(reference_top & comparison_top) / len(union)
            if rank_evaluable and union
            else None
        ),
    }


def build_ablation_comparison_summary(
    comparison: pd.DataFrame,
    *,
    baseline_valid: bool,
) -> pd.DataFrame:
    eligible = comparison[comparison["supported_effect_evaluable"].fillna(False).astype(bool)]
    rank_evaluable = baseline_valid and len(eligible) >= 2
    rows = [
        _comparison_summary_row(
            comparison,
            comparison_id="proxy_operational_vs_no_evolution",
            cohort="all_candidates",
            reference_score="no_evolution_score",
            comparison_score="proxy_operational_score",
            reference_rank="no_evolution_rank",
            comparison_rank="proxy_operational_rank",
            score_evaluable=baseline_valid,
            rank_evaluable=baseline_valid and len(comparison) >= 2,
        ),
        _comparison_summary_row(
            comparison,
            comparison_id="supported_operational_vs_no_evolution",
            cohort="all_candidates_evidence_gated",
            reference_score="no_evolution_score",
            comparison_score="supported_operational_score",
            reference_rank="no_evolution_rank",
            comparison_rank="supported_operational_rank",
            score_evaluable=baseline_valid and not eligible.empty,
            rank_evaluable=baseline_valid and not eligible.empty and len(comparison) >= 2,
        ),
        _comparison_summary_row(
            eligible,
            comparison_id="proxy_matched_vs_no_evolution",
            cohort="contract_supported_candidates",
            reference_score="no_evolution_score",
            comparison_score="proxy_matched_score",
            reference_rank="supported_subcohort_no_evolution_rank",
            comparison_rank="supported_subcohort_proxy_matched_rank",
            score_evaluable=baseline_valid and not eligible.empty,
            rank_evaluable=rank_evaluable,
        ),
        _comparison_summary_row(
            eligible,
            comparison_id="supported_matched_vs_no_evolution",
            cohort="contract_supported_candidates",
            reference_score="no_evolution_score",
            comparison_score="supported_matched_score",
            reference_rank="supported_subcohort_no_evolution_rank",
            comparison_rank="supported_subcohort_supported_matched_rank",
            score_evaluable=baseline_valid and not eligible.empty,
            rank_evaluable=rank_evaluable,
        ),
        _comparison_summary_row(
            eligible,
            comparison_id="supported_matched_vs_proxy_matched",
            cohort="contract_supported_candidates",
            reference_score="proxy_matched_score",
            comparison_score="supported_matched_score",
            reference_rank="supported_subcohort_proxy_matched_rank",
            comparison_rank="supported_subcohort_supported_matched_rank",
            score_evaluable=baseline_valid and not eligible.empty,
            rank_evaluable=rank_evaluable,
        ),
    ]
    return pd.DataFrame(rows)


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_report(path: Path, manifest: Mapping[str, Any], summary: pd.DataFrame) -> None:
    lines = [
        "# Stage 4H — Comparative evolutionary ablation",
        "",
        f"Analysis status: **{manifest['analysis_status']}**",
        f"Candidates: **{manifest['candidate_count']}**",
        (
            "Contract-supported candidates with evaluable paired scores: "
            f"**{manifest['supported_evaluable_candidate_count']}**"
        ),
        "",
        "## Comparisons",
        "",
        "| Comparison | Cohort | Status | Candidates | Mean score delta | Rank correlation |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in summary.to_dict(orient="records"):
        mean_delta = pd.to_numeric(
            pd.Series([row.get("mean_score_delta")]), errors="coerce"
        ).iloc[0]
        correlation = pd.to_numeric(
            pd.Series([row.get("rank_correlation")]), errors="coerce"
        ).iloc[0]
        lines.append(
            f"| `{row['comparison_id']}` | `{row['cohort']}` | "
            f"`{row['evaluation_status']}` | {int(row['candidate_count'])} | "
            f"{mean_delta if pd.notna(mean_delta) else 'not_evaluable'} | "
            f"{correlation if pd.notna(correlation) else 'not_evaluable'} |"
        )
    if manifest["supported_evaluable_candidate_count"] == 0:
        lines.extend(
            [
                "",
                "> No contract-supported candidate is currently evaluable. The supported effect is unknown, not zero.",
            ]
        )
    lines.extend(
        [
            "",
            "## Scientific guardrails",
            "",
            "- The operational proxy comparison remains exploratory.",
            "- The matched comparison uses the same candidates and evolutionary terms on both sides.",
            "- Biofilm and HGT are excluded from the matched comparison because "
            "they lack a Stage 4A explicit contract.",
            "- Unsupported candidates can move indirectly in a global rank when supported candidates move.",
            "- Missing supported evidence is never replaced with a proxy or interpreted as low risk.",
            "- Stage 4H does not change production scores, formulas, weights, or ranking.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_evolutionary_ablation_comparison_outputs(
    output_dir: Path,
    candidate_ablation: pd.DataFrame,
    candidate_coverage: pd.DataFrame | None,
    ablation_summary: Mapping[str, Any],
    *,
    ablation_source: Path | None = None,
    coverage_source: Path | None = None,
) -> dict[str, Any]:
    """Write Stage 4H outputs; missing Stage 4G coverage blocks the comparison."""

    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_available = candidate_coverage is not None
    coverage = candidate_coverage if candidate_coverage is not None else pd.DataFrame()
    comparison, mapping, metadata = build_evolutionary_ablation_comparison(
        candidate_ablation,
        coverage,
        ablation_summary,
    )
    if not coverage_available:
        metadata["analysis_status"] = "blocked_missing_stage4g_coverage"

    comparison_path = output_dir / "evolutionary_ablation_comparison_by_candidate.csv"
    summary_path = output_dir / "evolutionary_ablation_comparison_summary.csv"
    mapping_path = output_dir / "evolutionary_ablation_mapping_audit.csv"
    manifest_path = output_dir / "evolutionary_ablation_comparison_manifest.json"
    report_path = output_dir / "evolutionary_ablation_comparison_report.md"
    summary = pd.DataFrame(metadata.pop("summary_rows", []))
    if summary.empty:
        summary = pd.DataFrame(
            [
                {
                    "comparison_id": comparison_id,
                    "cohort": cohort,
                    "evaluation_status": metadata["analysis_status"],
                    "candidate_count": 0,
                    "mean_score_delta": None,
                    "median_score_delta": None,
                    "mean_absolute_score_delta": None,
                    "maximum_absolute_score_delta": None,
                    "promoted_count": None,
                    "demoted_count": None,
                    "unchanged_count": None,
                    "rank_correlation": None,
                    "top_k": None,
                    "top_k_overlap_count": None,
                    "top_k_jaccard": None,
                }
                for comparison_id, cohort in (
                    ("proxy_operational_vs_no_evolution", "all_candidates"),
                    (
                        "supported_operational_vs_no_evolution",
                        "all_candidates_evidence_gated",
                    ),
                    ("proxy_matched_vs_no_evolution", "contract_supported_candidates"),
                    ("supported_matched_vs_no_evolution", "contract_supported_candidates"),
                    (
                        "supported_matched_vs_proxy_matched",
                        "contract_supported_candidates",
                    ),
                )
            ]
        )
    comparison.to_csv(comparison_path, index=False)
    summary.to_csv(summary_path, index=False)
    mapping.to_csv(mapping_path, index=False)

    manifest = {
        "stage": "4H",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **metadata,
        "candidate_count": int(len(candidate_ablation)),
        "coverage_candidate_count": int(len(coverage)),
        "coverage_available": coverage_available,
        "source_modes": sorted(
            {
                _norm(value)
                for value in coverage.get("source_mode", pd.Series(dtype="string"))
                if _norm(value)
            }
        ),
        "scoring_effect": False,
        "scoring_formula_changed": False,
        "theory_weights_changed": False,
        "production_ranking_changed": False,
        "qualitative_evidence_numeric_conversion": False,
        "auto_promotion_enabled": False,
        "matched_comparison_excludes_biofilm_hgt": True,
        "unsupported_effect_is_zero": False,
        "inputs": {
            "ablation_source": str(ablation_source) if ablation_source else None,
            "ablation_source_sha256": _sha256(ablation_source),
            "coverage_source": str(coverage_source) if coverage_source else None,
            "coverage_source_sha256": _sha256(coverage_source),
        },
        "outputs": {
            "candidate_comparison": str(comparison_path),
            "summary": str(summary_path),
            "mapping_audit": str(mapping_path),
            "manifest": str(manifest_path),
            "report": str(report_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    _write_report(report_path, manifest, summary)
    return manifest
