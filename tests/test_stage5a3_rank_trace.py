from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.stage5a3_rank_trace import (
    build_stage5a3_rank_trace,
    run_stage5a3_rank_trace,
)


def _audit() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "benchmark_token": "pbp1A",
                "benchmark_requested": True,
                "benchmark_match_type": "alias_accession",
                "benchmark_alias_used": "O25319",
                "candidate_seed_accession": "O25319",
                "protein_id": "O25319",
                "gene": "HP_0597",
                "discovered_naturally": True,
                "benchmark_forced_candidate": False,
                "seed_initial_rank": 727,
                "seed_selected_rank": 727,
                "selected_for_scoring": True,
                "final_rank": 460,
                "final_score": 0.445791,
                "final_score_column": "nodo_score",
            },
            {
                "benchmark_token": "gyrA",
                "benchmark_requested": True,
                "benchmark_match_type": "canonical_gene_exact",
                "benchmark_alias_used": "",
                "candidate_seed_accession": "P48370",
                "protein_id": "P48370",
                "gene": "gyrA",
                "discovered_naturally": True,
                "benchmark_forced_candidate": False,
                "seed_initial_rank": 231,
                "seed_selected_rank": 231,
                "selected_for_scoring": True,
                "final_rank": 1554,
                "final_score": 0.405971,
                "final_score_column": "nodo_score",
            },
        ]
    )


def _ranking() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protein_id": "O25319",
                "gene": "HP_0597",
                "included_in_therapeutic_ranking": True,
                "meta_priority_score_v3": 0.61,
                "evidence_quality_score": 0.3811,
                "functional_node_theory_score": 0.19150,
                "functional_node_theory_confidence": 0.25,
                "functional_node_theory_label": "hypothesis_only_insufficient_evidence",
                "confidence_ceiling": 0.25,
                "meta_priority_score_v2": 0.52,
                "nodo_score": 0.445791,
                "evolutionary_escape_risk_score": 0.514025,
                "redundancy_penalty": 0.5,
            },
            {
                "protein_id": "X00001",
                "gene": "other",
                "included_in_therapeutic_ranking": True,
                "meta_priority_score_v3": 0.55,
                "evidence_quality_score": 0.5,
                "functional_node_theory_score": 0.18000,
                "confidence_ceiling": 0.5,
                "meta_priority_score_v2": 0.50,
                "nodo_score": 0.50,
            },
            {
                "protein_id": "P48370",
                "gene": "gyrA",
                "included_in_therapeutic_ranking": True,
                "meta_priority_score_v3": 0.40,
                "evidence_quality_score": 0.3811,
                "functional_node_theory_score": 0.16798,
                "functional_node_theory_confidence": 0.25,
                "functional_node_theory_label": "hypothesis_only_insufficient_evidence",
                "confidence_ceiling": 0.25,
                "meta_priority_score_v2": 0.41,
                "nodo_score": 0.405971,
                "evolutionary_escape_risk_score": 0.611250,
                "redundancy_penalty": 0.5,
            },
        ]
    )


def _phase3() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protein_id": "O25319",
                "gene": "HP_0597",
                "meta_priority_score_v3": 0.61,
                "rank_phase3_real_candidates": 1,
                "rank_phase3_all_records": 1,
                "functional_node_theory_score": 0.19150,
                "phase3_evidence_confidence_label": "low",
                "phase3_recommendation": "hypothesis_only",
            },
            {
                "protein_id": "P48370",
                "gene": "gyrA",
                "meta_priority_score_v3": 0.40,
                "rank_phase3_real_candidates": 3,
                "rank_phase3_all_records": 3,
                "functional_node_theory_score": 0.16798,
                "phase3_evidence_confidence_label": "low",
                "phase3_recommendation": "hypothesis_only",
            },
            {
                "protein_id": "X00001",
                "gene": "other",
                "meta_priority_score_v3": 0.55,
                "rank_phase3_real_candidates": 2,
                "rank_phase3_all_records": 2,
                "functional_node_theory_score": 0.18000,
            },
        ]
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_primary_score_semantics_use_meta_priority_v3_not_legacy_nodo_score():
    trace, summary = build_stage5a3_rank_trace(_audit(), _ranking(), _phase3())
    pbp = trace.loc[trace["benchmark_token"] == "pbp1A"].iloc[0]

    assert summary["primary_score_column"] == "meta_priority_score_v3"
    assert pbp["therapeutic_primary_score"] == pytest.approx(0.61)
    assert pbp["stage5a2_reported_score_legacy"] == pytest.approx(0.445791)
    assert pbp["stage5a2_reported_score_column_legacy"] == "nodo_score"
    assert not bool(pbp["legacy_score_matches_primary_semantics"])


def test_final_rank_is_existing_ranking_row_order_without_resorting():
    ranking = _ranking().iloc[[2, 0, 1]].reset_index(drop=True)
    trace, summary = build_stage5a3_rank_trace(_audit(), ranking, _phase3())

    gyra = trace.loc[trace["benchmark_token"] == "gyrA"].iloc[0]
    pbp = trace.loc[trace["benchmark_token"] == "pbp1A"].iloc[0]

    assert summary["final_rank_definition"] == "1_based_row_order_in_ranking_nodos.csv"
    assert gyra["final_rank"] == 1
    assert pbp["final_rank"] == 2


def test_fnt_rank_and_rank_deltas_are_explicit():
    trace, _ = build_stage5a3_rank_trace(_audit(), _ranking(), _phase3())
    pbp = trace.loc[trace["benchmark_token"] == "pbp1A"].iloc[0]
    gyra = trace.loc[trace["benchmark_token"] == "gyrA"].iloc[0]

    assert pbp["functional_node_theory_rank"] == 1
    assert gyra["functional_node_theory_rank"] == 3
    assert pbp["seed_to_fnt_rank_delta"] == 1 - 727
    assert pbp["fnt_to_final_rank_delta"] == 1 - 1
    assert gyra["fnt_to_final_rank_delta"] == 3 - 3


def test_sort_trace_records_actual_reporting_sort_columns_and_values():
    trace, summary = build_stage5a3_rank_trace(_audit(), _ranking(), _phase3())
    pbp = trace.loc[trace["benchmark_token"] == "pbp1A"].iloc[0]

    assert summary["ranking_sort_columns"] == [
        "included_in_therapeutic_ranking",
        "meta_priority_score_v3",
        "evidence_quality_score",
        "functional_node_theory_score",
        "confidence_ceiling",
        "meta_priority_score_v2",
    ]
    values = json.loads(pbp["therapeutic_sort_values"])
    assert values["meta_priority_score_v3"] == pytest.approx(0.61)
    assert values["functional_node_theory_score"] == pytest.approx(0.19150)


def test_run_stage5a3_writes_new_outputs_without_modifying_source_files(tmp_path: Path):
    run = tmp_path / "run"
    results = run / "workspace" / "results"
    processed = run / "workspace" / "data_processed"
    review = run / "review_package"
    results.mkdir(parents=True)
    processed.mkdir(parents=True)
    review.mkdir()

    audit_path = results / "stage5a2_candidate_seed_audit.csv"
    ranking_path = results / "ranking_nodos.csv"
    phase3_path = processed / "phase3_features.csv"

    _audit().to_csv(audit_path, index=False)
    _ranking().to_csv(ranking_path, index=False)
    _phase3().to_csv(phase3_path, index=False)
    (results / "stage5a2_manifest.json").write_text(
        json.dumps(
            {
                "organism": "Helicobacter pylori",
                "strain": "26695",
                "taxon_id": "85962",
                "proteome_id": "UP000000429",
            }
        ),
        encoding="utf-8",
    )

    before = {path: _sha(path) for path in (audit_path, ranking_path, phase3_path)}
    result = run_stage5a3_rank_trace(run)
    after = {path: _sha(path) for path in (audit_path, ranking_path, phase3_path)}

    assert before == after
    assert result["audit_status"] == "completed"
    assert (results / "stage5a3_rank_trace.csv").exists()
    assert (results / "stage5a3_manifest.json").exists()
    assert (review / "stage5a3_rank_trace.csv").exists()
    assert (review / "stage5a3_manifest.json").exists()

    manifest = json.loads((results / "stage5a3_manifest.json").read_text(encoding="utf-8"))
    assert manifest["providers_rerun"] is False
    assert manifest["scoring_recomputed"] is False
    assert manifest["ranking_order_changed"] is False
    assert manifest["scoring_model_changed"] is False
    assert manifest["functional_node_theory_weights_changed"] is False


def test_missing_required_stage5a2_output_fails_explicitly(tmp_path: Path):
    run = tmp_path / "run"
    (run / "workspace" / "results").mkdir(parents=True)
    (run / "workspace" / "data_processed").mkdir(parents=True)

    with pytest.raises(ValueError, match="required input missing"):
        run_stage5a3_rank_trace(run)
