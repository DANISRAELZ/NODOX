from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest

from src.nodos_funcionales.evolutionary_ablation_comparison import (
    build_ablation_coverage_mapping_audit,
    build_evolutionary_ablation_comparison,
    write_evolutionary_ablation_comparison_outputs,
)


def _ablation_row(
    candidate_id: str,
    *,
    supported: bool = False,
    no_evolution_score: float = 0.70,
    proxy_score: float = 0.60,
    matched_proxy_score: float = 0.66,
    supported_score: float = 0.64,
    no_evolution_rank: int = 1,
    proxy_rank: int = 1,
    matched_proxy_rank: int = 1,
    supported_rank: int = 1,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "protein_id": candidate_id,
        "gene": candidate_id.lower(),
        "ranking_without_evolutionary_information_score": no_evolution_score,
        "ranking_without_evolutionary_information_rank": no_evolution_rank,
        "ranking_with_proxy_evolutionary_score": proxy_score,
        "ranking_with_proxy_evolutionary_rank": proxy_rank,
        "ranking_with_supported_evolutionary_score": (
            supported_score if supported else no_evolution_score
        ),
        "ranking_with_supported_evolutionary_rank": supported_rank,
        "ranking_with_matched_proxy_evolutionary_score": (
            matched_proxy_score if supported else no_evolution_score
        ),
        "ranking_with_matched_proxy_evolutionary_rank": matched_proxy_rank,
        "supported_evolutionary_dimension_applied": supported,
        "evolutionary_evidence_contract_supported": supported,
    }


def _coverage_row(
    candidate_id: str,
    *,
    explicit_count: int = 0,
    group_count: int = 0,
    supported: bool = False,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "explicit_variable_count": explicit_count,
        "reported_explicit_variable_count": explicit_count,
        "contract_count_consistent": True,
        "explicit_variables": "v1; v2; v3" if explicit_count >= 3 else "none",
        "proxy_variable_count": 7 - explicit_count,
        "proxy_variables": "proxy_variables" if explicit_count < 7 else "none",
        "quantitative_evidence_variable_count": explicit_count,
        "qualitative_evidence_variable_count": 1,
        "qualitative_evidence_record_count": 2,
        "independent_evidence_group_count": group_count,
        "independence_groups": "g1; g2" if group_count >= 2 else "none",
        "missing_variables": "missing" if explicit_count < 7 else "none",
        "missingness_by_variable": "fitness_cost_of_escape=numeric_value_not_extractable",
        "coverage_bin": (
            "3_or_more_explicit_variables" if explicit_count >= 3 else "0_explicit_variables"
        ),
        "minimum_explicit_variables": 3,
        "minimum_independent_evidence_groups": 2,
        "meets_explicit_variable_threshold": explicit_count >= 3,
        "meets_independence_threshold": group_count >= 2,
        "evolutionary_evidence_contract_supported": supported,
        "evolutionary_dimension_support_status": (
            "supported_explicit" if supported else "proxy_only_or_missing"
        ),
        "source_mode": "hybrid_curated",
    }


def _summary(valid: bool = True) -> dict[str, object]:
    return {"baseline_reconstruction_valid": valid}


def test_all_proxy_candidates_report_supported_effect_as_not_evaluable() -> None:
    ablation = pd.DataFrame([_ablation_row("A"), _ablation_row("B", no_evolution_rank=2, proxy_rank=2)])
    coverage = pd.DataFrame([_coverage_row("A"), _coverage_row("B")])

    comparison, mapping, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary()
    )
    summary = pd.DataFrame(metadata["summary_rows"]).set_index("comparison_id")

    assert mapping["analysis_eligible"].all()
    assert metadata["analysis_status"] == "not_evaluable_no_supported_candidates"
    assert metadata["supported_evaluable_candidate_count"] == 0
    assert comparison["supported_effect_evaluable"].eq(False).all()  # noqa: E712
    assert comparison["supported_matched_score"].isna().all()
    assert summary.loc["proxy_operational_vs_no_evolution", "evaluation_status"] == "evaluable"
    assert summary.loc["supported_matched_vs_no_evolution", "evaluation_status"] == "not_evaluable"
    assert pd.isna(summary.loc["supported_matched_vs_no_evolution", "mean_score_delta"])


def test_one_supported_candidate_has_score_comparison_but_not_rank_comparison() -> None:
    ablation = pd.DataFrame([_ablation_row("A", supported=True)])
    coverage = pd.DataFrame([_coverage_row("A", explicit_count=3, group_count=2, supported=True)])

    comparison, _, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary()
    )
    summary = pd.DataFrame(metadata["summary_rows"]).set_index("comparison_id")

    assert metadata["analysis_status"] == "comparison_evaluable"
    assert metadata["supported_evaluable_candidate_count"] == 1
    assert not metadata["paired_rank_comparison_evaluable"]
    assert bool(comparison.loc[0, "supported_effect_evaluable"])
    assert comparison.loc[0, "supported_minus_proxy_matched_score"] == pytest.approx(-0.02)
    assert (
        summary.loc["supported_matched_vs_proxy_matched", "evaluation_status"]
        == "score_only_rank_not_evaluable"
    )
    assert summary.loc["supported_matched_vs_proxy_matched", "mean_score_delta"] == pytest.approx(-0.02)
    assert pd.isna(summary.loc["supported_matched_vs_proxy_matched", "rank_correlation"])


def test_supported_subcohort_uses_paired_terms_and_marks_indirect_global_shift() -> None:
    ablation = pd.DataFrame(
        [
            _ablation_row(
                "A",
                supported=True,
                no_evolution_score=0.90,
                proxy_score=0.70,
                matched_proxy_score=0.80,
                supported_score=0.60,
                no_evolution_rank=1,
                proxy_rank=2,
                matched_proxy_rank=2,
                supported_rank=3,
            ),
            _ablation_row(
                "B",
                supported=True,
                no_evolution_score=0.80,
                proxy_score=0.85,
                matched_proxy_score=0.82,
                supported_score=0.88,
                no_evolution_rank=2,
                proxy_rank=1,
                matched_proxy_rank=1,
                supported_rank=1,
            ),
            _ablation_row(
                "C",
                supported=False,
                no_evolution_score=0.70,
                proxy_score=0.65,
                no_evolution_rank=3,
                proxy_rank=3,
                matched_proxy_rank=3,
                supported_rank=2,
            ),
        ]
    )
    coverage = pd.DataFrame(
        [
            _coverage_row("A", explicit_count=3, group_count=2, supported=True),
            _coverage_row("B", explicit_count=4, group_count=2, supported=True),
            _coverage_row("C"),
        ]
    )

    comparison, _, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary()
    )
    indexed = comparison.set_index("candidate_id")
    summary = pd.DataFrame(metadata["summary_rows"]).set_index("comparison_id")

    assert metadata["paired_rank_comparison_evaluable"]
    assert indexed.loc["C", "supported_global_rank_effect_attribution"] == "indirect_cohort_rank_shift"
    assert pd.isna(indexed.loc["C", "supported_matched_score"])
    assert indexed.loc["A", "proxy_matched_score"] == 0.80
    assert indexed.loc["A", "supported_matched_score"] == 0.60
    assert summary.loc["supported_matched_vs_proxy_matched", "candidate_count"] == 2
    assert summary.loc["supported_matched_vs_proxy_matched", "evaluation_status"] == "evaluable"


def test_three_variables_from_one_group_remain_not_evaluable() -> None:
    ablation = pd.DataFrame([_ablation_row("A")])
    coverage = pd.DataFrame([_coverage_row("A", explicit_count=3, group_count=1)])

    comparison, _, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary()
    )

    assert metadata["supported_evaluable_candidate_count"] == 0
    assert comparison.loc[0, "supported_effect_status"] == (
        "not_evaluable_insufficient_independent_evidence"
    )


def test_duplicate_or_missing_candidate_mapping_blocks_comparison() -> None:
    ablation = pd.DataFrame([_ablation_row("A"), _ablation_row("A")])
    coverage = pd.DataFrame([_coverage_row("A")])

    comparison, mapping, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary()
    )

    assert comparison.empty
    assert metadata["analysis_status"] == "blocked_candidate_mapping"
    assert mapping.loc[0, "mapping_status"] == "duplicate_ablation_candidate_id"


def test_baseline_mismatch_blocks_supported_interpretation() -> None:
    ablation = pd.DataFrame([_ablation_row("A", supported=True)])
    coverage = pd.DataFrame([_coverage_row("A", explicit_count=3, group_count=2, supported=True)])

    comparison, _, metadata = build_evolutionary_ablation_comparison(
        ablation, coverage, _summary(False)
    )

    assert metadata["analysis_status"] == "blocked_baseline_reconstruction"
    assert not bool(comparison.loc[0, "supported_effect_evaluable"])
    assert comparison.loc[0, "supported_effect_status"] == (
        "not_evaluable_baseline_reconstruction_failed"
    )


def test_writer_is_read_only_and_declares_no_scoring_effect(tmp_path: Path) -> None:
    ablation = pd.DataFrame([_ablation_row("A", supported=True)])
    coverage = pd.DataFrame([_coverage_row("A", explicit_count=3, group_count=2, supported=True)])
    original_ablation = ablation.copy(deep=True)
    original_coverage = coverage.copy(deep=True)

    manifest = write_evolutionary_ablation_comparison_outputs(
        tmp_path, ablation, coverage, _summary()
    )

    pdt.assert_frame_equal(ablation, original_ablation)
    pdt.assert_frame_equal(coverage, original_coverage)
    assert manifest["scoring_effect"] is False
    assert manifest["scoring_formula_changed"] is False
    assert manifest["theory_weights_changed"] is False
    assert manifest["production_ranking_changed"] is False
    assert manifest["qualitative_evidence_numeric_conversion"] is False
    assert manifest["auto_promotion_enabled"] is False
    for filename in (
        "evolutionary_ablation_comparison_by_candidate.csv",
        "evolutionary_ablation_comparison_summary.csv",
        "evolutionary_ablation_mapping_audit.csv",
        "evolutionary_ablation_comparison_manifest.json",
        "evolutionary_ablation_comparison_report.md",
    ):
        assert (tmp_path / filename).exists()
    written = json.loads(
        (tmp_path / "evolutionary_ablation_comparison_manifest.json").read_text()
    )
    assert written["stage"] == "4H"


def test_missing_stage4g_coverage_writes_blocked_manifest(tmp_path: Path) -> None:
    manifest = write_evolutionary_ablation_comparison_outputs(
        tmp_path,
        pd.DataFrame([_ablation_row("A")]),
        None,
        _summary(),
    )

    assert manifest["analysis_status"] == "blocked_missing_stage4g_coverage"
    assert manifest["coverage_available"] is False
    assert manifest["supported_evaluable_candidate_count"] == 0


def test_online_strict_mode_is_preserved_without_loading_curated_evidence(tmp_path: Path) -> None:
    coverage_row = _coverage_row("A")
    coverage_row["source_mode"] = "online_strict"
    manifest = write_evolutionary_ablation_comparison_outputs(
        tmp_path,
        pd.DataFrame([_ablation_row("A")]),
        pd.DataFrame([coverage_row]),
        _summary(),
    )
    comparison = pd.read_csv(
        tmp_path / "evolutionary_ablation_comparison_by_candidate.csv"
    )

    assert manifest["source_modes"] == ["online_strict"]
    assert manifest["analysis_status"] == "not_evaluable_no_supported_candidates"
    assert comparison.loc[0, "source_mode"] == "online_strict"
    assert pd.isna(comparison.loc[0, "supported_matched_score"])


def test_mapping_audit_never_falls_back_to_gene() -> None:
    ablation = pd.DataFrame([{"candidate_id": "A", "gene": "same"}])
    coverage = pd.DataFrame([{"candidate_id": "B", "gene": "same"}])

    audit = build_ablation_coverage_mapping_audit(ablation, coverage)

    assert set(audit["mapping_status"]) == {"missing_in_ablation", "missing_in_stage4g_coverage"}
    assert not audit["analysis_eligible"].any()
