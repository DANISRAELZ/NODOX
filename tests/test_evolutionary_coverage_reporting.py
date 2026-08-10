from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from src.nodos_funcionales.evolutionary_coverage_reporting import (
    COVERAGE_BINS,
    build_candidate_evolutionary_coverage,
    build_evolutionary_coverage_distribution,
    build_evolutionary_evidence_records,
    resolve_screened_literature_to_candidates,
    write_evolutionary_coverage_outputs,
)
from src.nodos_funcionales.evolutionary_evidence_contract import EVOLUTIONARY_VARIABLES


def _config(mode: str = "hybrid_curated") -> dict:
    return {
        "online_sources": {"source_mode_effective": mode},
        "evolutionary_escape_risk": {
            "minimum_explicit_variables": 3,
            "minimum_independent_evidence_groups": 2,
        },
        "curated_real_evidence": {
            "enabled": True,
            "base_dir": "data_curated/organisms",
        },
    }


def _candidate(
    candidate_id: str,
    gene: str,
    explicit_variables: tuple[str, ...] = (),
    *,
    groups: tuple[str, ...] = (),
    supported: bool = False,
) -> dict:
    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "protein_id": candidate_id,
        "gene": gene,
        "taxon_id": "210",
        "organism": "Helicobacter pylori",
        "strain": "G27",
        "evolutionary_escape_risk_explicit_variable_count": len(explicit_variables),
        "evolutionary_escape_risk_independent_evidence_group_count": len(groups),
        "evolutionary_escape_risk_independence_groups": "; ".join(groups) or "none",
        "evolutionary_evidence_contract_supported": supported,
        "evolutionary_escape_proxy_score": 0.55,
        "evolutionary_escape_supported_score": 0.42 if supported else float("nan"),
        "evolutionary_escape_proxy_penalty_applied": 0.08,
        "evolutionary_escape_supported_penalty_applied": 0.06 if supported else 0.0,
        "evolutionary_evidence_contract_errors": "none",
        "evolutionary_evidence_contract_warnings": "none",
    }
    for variable in EVOLUTIONARY_VARIABLES:
        explicit = variable in explicit_variables
        row[variable] = 0.6
        row[f"{variable}_is_explicit"] = explicit
        row[f"{variable}_contract_explicit"] = explicit
        row[f"{variable}_source_type"] = "experimental" if explicit else "derived"
        row[f"{variable}_source_database"] = "test_database" if explicit else ""
        row[f"{variable}_source_record"] = f"record:{candidate_id}:{variable}" if explicit else ""
        row[f"{variable}_source_version"] = "v1" if explicit else ""
        row[f"{variable}_retrieved_at"] = "2026-08-10T12:00:00Z" if explicit else ""
        row[f"{variable}_mapping_method"] = "test_exact_mapping" if explicit else ""
        row[f"{variable}_mapping_status"] = "exact_gene_and_taxon" if explicit else ""
        row[f"{variable}_evidence_status"] = "observed" if explicit else ""
        row[f"{variable}_evidence_confidence"] = "high" if explicit else ""
        row[f"{variable}_independence_group"] = groups[0] if explicit and groups else ""
        row[f"{variable}_method_scope"] = "test method" if explicit else ""
        row[f"{variable}_taxon_id"] = "210" if explicit else ""
        row[f"{variable}_notes"] = "test evidence" if explicit else ""
    return row


def _screened_row(
    *,
    mutation: str = "V374L",
    finding_direction: str = "fitness_defect",
    relative_fitness: str = "",
) -> dict:
    return {
        "gene": "pbp1",
        "taxon_id": "210",
        "mutation": mutation,
        "assay_context": "24-hour competition against wild-type G27",
        "finding_direction": finding_direction,
        "relative_fitness": relative_fitness,
        "derived_screening_status": (
            "quantitative_candidate_not_promoted"
            if relative_fitness
            else "screening_only_missing_numeric_relative_fitness"
        ),
        "screening_reason": "numeric value unavailable" if not relative_fitness else "awaiting promotion",
        "source_type": "literature_curated",
        "source_database": "Helicobacter",
        "source_record": "PMID:32677105",
        "source_version": "version_of_record_2020",
        "retrieved_at": "2026-08-07T19:52:00Z",
        "mapping_method": "exact gene+mutation+taxon literature curation",
        "mapping_status": "exact_gene_and_taxon",
        "evidence_status": "observed",
        "evidence_confidence": "high",
        "method_scope": "isogenic competition assay",
        "pmid": "32677105",
        "doi": "10.1111/hel.12724",
        "notes": "screening-only test record",
    }


def test_distribution_reports_zero_one_two_and_three_or_more_bins() -> None:
    features = pd.DataFrame(
        [
            _candidate("C0", "gene0"),
            _candidate("C1", "gene1", (EVOLUTIONARY_VARIABLES[0],), groups=("group_a",)),
            _candidate("C2", "gene2", EVOLUTIONARY_VARIABLES[:2], groups=("group_a", "group_b")),
            _candidate(
                "C3",
                "gene3",
                EVOLUTIONARY_VARIABLES[:3],
                groups=("group_a", "group_b"),
                supported=True,
            ),
        ]
    )

    records = build_evolutionary_evidence_records(features, pd.DataFrame(), _config())
    coverage = build_candidate_evolutionary_coverage(features, records, _config())
    distribution = build_evolutionary_coverage_distribution(coverage)

    assert list(distribution["coverage_bin"]) == list(COVERAGE_BINS)
    assert list(distribution["candidate_count"]) == [1, 1, 1, 1]
    indexed = coverage.set_index("candidate_id")
    assert indexed.loc["C3", "coverage_bin"] == "3_or_more_explicit_variables"
    assert bool(indexed.loc["C3", "evolutionary_evidence_contract_supported"])
    assert indexed.loc["C0", "quantitative_evidence_variable_count"] == 0
    assert indexed.loc["C3", "quantitative_evidence_variable_count"] == 3


def test_three_variables_from_one_group_meet_coverage_but_not_contract() -> None:
    features = pd.DataFrame(
        [_candidate("C", "gene", EVOLUTIONARY_VARIABLES[:3], groups=("one_group",), supported=False)]
    )
    records = build_evolutionary_evidence_records(features, pd.DataFrame(), _config())
    coverage = build_candidate_evolutionary_coverage(features, records, _config()).iloc[0]

    assert coverage["explicit_variable_count"] == 3
    assert bool(coverage["meets_explicit_variable_threshold"]) is True
    assert bool(coverage["meets_independence_threshold"]) is False
    assert coverage["evolutionary_dimension_support_status"] == "explicit_threshold_met_independence_failed"


def test_qualitative_stage4f_records_remain_non_scoring_and_do_not_increase_count() -> None:
    features = pd.DataFrame([_candidate("PBP1", "pbp1")])
    screening = pd.DataFrame(
        [
            _screened_row(mutation="V374L"),
            _screened_row(mutation="N562Y", finding_direction="conditional_fitness_advantage"),
        ]
    )

    records = build_evolutionary_evidence_records(features, screening, _config())
    coverage = build_candidate_evolutionary_coverage(features, records, _config()).iloc[0]
    screened = records[records["record_scope"].eq("screened_literature")]

    assert len(screened) == 2
    assert screened["evidence_form"].eq("qualitative").all()
    assert screened["missingness_reason"].eq("numeric_value_not_extractable").all()
    assert screened["affects_proxy_scoring"].eq(False).all()  # noqa: E712
    assert screened["affects_supported_scoring"].eq(False).all()  # noqa: E712
    assert coverage["explicit_variable_count"] == 0
    assert coverage["qualitative_evidence_record_count"] == 2
    assert "fitness_cost_of_escape=numeric_value_not_extractable" in coverage["missingness_by_variable"]


def test_quantitative_screening_candidate_is_visible_but_not_promoted_to_scoring() -> None:
    features = pd.DataFrame([_candidate("PBP1", "pbp1")])
    screening = pd.DataFrame([_screened_row(relative_fitness="0.82")])

    records = build_evolutionary_evidence_records(features, screening, _config())
    screened = records[records["record_scope"].eq("screened_literature")].iloc[0]
    coverage = build_candidate_evolutionary_coverage(features, records, _config()).iloc[0]

    assert screened["evidence_form"] == "quantitative"
    assert screened["missingness_reason"] == "quantitative_evidence_available"
    assert bool(screened["variable_scoring_eligible"]) is False
    assert bool(screened["affects_supported_scoring"]) is False
    assert coverage["explicit_variable_count"] == 0


def test_ambiguous_gene_taxon_screening_record_is_not_fanned_out() -> None:
    features = pd.DataFrame([_candidate("P1", "pbp1"), _candidate("P2", "pbp1")])
    screening = pd.DataFrame([_screened_row()])

    resolved = resolve_screened_literature_to_candidates(
        features,
        screening,
        source_mode="hybrid_curated",
    )

    assert len(resolved) == 1
    assert resolved.loc[0, "candidate_id"] == ""
    assert resolved.loc[0, "coverage_mapping_status"] == "ambiguous_gene_and_taxon"
    assert resolved.loc[0, "missingness_reason"] == "mutation_not_mappable_to_candidate"


def test_writer_preserves_input_and_declares_no_scoring_effect(tmp_path: Path) -> None:
    features = pd.DataFrame(
        [
            _candidate(
                "C3",
                "gene3",
                EVOLUTIONARY_VARIABLES[:3],
                groups=("group_a", "group_b"),
                supported=True,
            )
        ]
    )
    original = features.copy(deep=True)

    manifest = write_evolutionary_coverage_outputs(
        tmp_path,
        features,
        _config(),
        screening_summary=pd.DataFrame(),
    )

    pdt.assert_frame_equal(features, original)
    assert manifest["scoring_effect"] is False
    assert manifest["scoring_formula_changed"] is False
    assert manifest["theory_weights_changed"] is False
    assert manifest["auto_promotion_enabled"] is False
    for filename in (
        "evolutionary_coverage_evidence_records.csv",
        "evolutionary_coverage_by_candidate.csv",
        "evolutionary_coverage_distribution.csv",
        "evolutionary_coverage_manifest.json",
        "evolutionary_coverage_report.md",
    ):
        assert (tmp_path / "results" / filename).exists()


def test_online_strict_disables_local_screening_but_still_writes_coverage(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir(parents=True)
    (tmp_path / "results" / "organism_profile.json").write_text(
        json.dumps({"organism": "Helicobacter pylori", "taxon_id": 210}),
        encoding="utf-8",
    )
    screening_dir = tmp_path / "data_curated" / "organisms" / "helicobacter_pylori"
    screening_dir.mkdir(parents=True)
    pd.DataFrame([_screened_row()]).to_csv(
        screening_dir / "evolutionary_fitness_cost_screened.csv",
        index=False,
    )
    features = pd.DataFrame([_candidate("PBP1", "pbp1")])

    manifest = write_evolutionary_coverage_outputs(tmp_path, features, _config("online_strict"))
    records = pd.read_csv(tmp_path / "results" / "evolutionary_coverage_evidence_records.csv")
    screening_manifest = json.loads(
        (tmp_path / "results" / "evolutionary_fitness_cost_literature_screening_manifest.json").read_text()
    )

    assert manifest["status"] == "coverage_reported"
    assert manifest["screened_literature_record_count"] == 0
    assert records["record_scope"].eq("canonical_scoring_input").all()
    assert screening_manifest["reason"] == "disabled_by_online_strict_policy"
    fitness = records[records["evolutionary_variable"].eq("fitness_cost_of_escape")].iloc[0]
    assert fitness["missingness_reason"] == "source_mode_disallows_curated_evidence"
