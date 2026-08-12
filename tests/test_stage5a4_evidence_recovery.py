from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales import stage5a4_evidence_recovery as stage5a4


def test_build_coverage_table_marks_recovered_score_affecting_evidence():
    before = pd.DataFrame(
        [
            {
                "layer_key": "functional_network",
                "provider_name": "string_api",
                "retrieval_status": "provider_unavailable",
                "usable_evidence": False,
                "affects_score": False,
                "matched_candidate_count": 0,
                "evidence_level": "unresolved",
            }
        ]
    )
    after = pd.DataFrame(
        [
            {
                "layer_key": "functional_network",
                "provider_name": "string_api",
                "retrieval_status": "api_real",
                "usable_evidence": True,
                "affects_score": True,
                "matched_candidate_count": 100,
                "evidence_level": "computational_online_evidence",
            }
        ]
    )

    result = stage5a4.build_coverage_table(before, after, candidate_count=200)
    row = result.loc[result["layer_key"].eq("functional_network")].iloc[0]

    assert bool(row["usable_evidence_recovered"]) is True
    assert bool(row["score_affecting_evidence_recovered"]) is True
    assert row["after_coverage_fraction"] == 0.5


def test_build_coverage_table_preserves_unresolved_missing_layers():
    result = stage5a4.build_coverage_table(pd.DataFrame(), candidate_count=10)
    row = result.loc[result["layer_key"].eq("contextual_essentiality")].iloc[0]

    assert bool(row["before_usable_evidence"]) is False
    assert row["before_matched_candidate_count"] == 0
    assert row["before_coverage_fraction"] == 0.0


def test_resolve_provider_dataset_uses_explicit_override(monkeypatch, tmp_path):
    configured = tmp_path / "configured.csv"
    version = tmp_path / "configured.version.txt"
    version.write_text("2026-08-12", encoding="utf-8")
    override = tmp_path / "override.csv"
    override.write_text("protein_id,gene\nP1,g1\n", encoding="utf-8")

    monkeypatch.setattr(
        stage5a4,
        "_configured_dataset",
        lambda project_root, provider: (configured, version),
    )

    result = stage5a4.resolve_provider_dataset(tmp_path, "deg", override)

    assert result["exists"] is True
    assert result["source"] == "explicit_override"
    assert result["path"] == str(override.resolve())
    assert result["version_recorded"] is True


def test_diamond_preflight_requires_reference_for_execute(tmp_path):
    result = stage5a4._diamond_preflight(
        tmp_path,
        enabled=True,
        execution_mode="execute",
        reference_fasta=None,
        database_prefix=None,
        cached_tsv=None,
    )

    assert result["ready"] is False
    assert result["reason"] == "execute_requires_reference_fasta"


def test_diamond_preflight_accepts_cached_tsv(tmp_path):
    cached = tmp_path / "diamond.tsv"
    cached.write_text("qseqid\tsseqid\n", encoding="utf-8")

    result = stage5a4._diamond_preflight(
        tmp_path,
        enabled=True,
        execution_mode="cache_only",
        reference_fasta=None,
        database_prefix=None,
        cached_tsv=cached,
    )

    assert result["ready"] is True
    assert result["cached_tsv_exists"] is True


def test_build_benchmark_comparison_uses_recovery_row_order_and_v3_score():
    source = pd.DataFrame(
        [
            {
                "benchmark_token": "pbp1A",
                "protein_id": "O25319",
                "gene": "HP_0597",
                "final_rank": 460,
                "therapeutic_primary_score": 0.16,
                "functional_node_theory_score": 0.19,
                "evidence_quality_score": 0.38,
            }
        ]
    )
    recovery = pd.DataFrame(
        [
            {
                "protein_id": "OTHER",
                "gene": "x",
                "meta_priority_score_v3": 0.30,
                "functional_node_theory_score": 0.40,
                "evidence_quality_score": 0.60,
            },
            {
                "protein_id": "O25319",
                "gene": "HP_0597",
                "meta_priority_score_v3": 0.20,
                "functional_node_theory_score": 0.25,
                "evidence_quality_score": 0.50,
                "phase3_evidence_confidence_label": "improved",
            },
        ]
    )

    result = stage5a4.build_benchmark_comparison(source, recovery)
    row = result.iloc[0]

    assert bool(row["recovery_match"]) is True
    assert row["after_final_rank"] == 2
    assert row["after_meta_priority_score_v3"] == pytest.approx(0.20)
    assert row["meta_priority_score_v3_delta"] == pytest.approx(0.04)
    assert row["evidence_quality_score_delta"] == pytest.approx(0.12)
