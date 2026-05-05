from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from src.nodos_funcionales.ranking_snapshots import build_ranking_snapshot, compare_ranking_snapshots
from tests.helpers import PROJECT_ROOT


@pytest.mark.unit
@pytest.mark.snapshot
def test_build_ranking_snapshot_keeps_stable_columns_and_rounding() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["B", "A"],
            "gene": ["b", "a"],
            "meta_priority_score": [0.123456789, 0.9],
            "therapeutic_role": ["low_priority_candidate", "bactericidal_candidate"],
        },
        index=[2, 1],
    )
    ranking.index.name = "rank"

    snapshot = build_ranking_snapshot(ranking)

    assert snapshot.columns.tolist() == [
        "rank",
        "protein_id",
        "gene",
        "meta_priority_score",
        "therapeutic_role",
    ]
    assert snapshot.loc[0, "rank"] == 1
    assert snapshot.loc[0, "meta_priority_score"] == 0.9
    assert snapshot.loc[1, "meta_priority_score"] == 0.123457


@pytest.mark.unit
@pytest.mark.snapshot
def test_compare_ranking_snapshots_reports_rank_and_score_drift() -> None:
    reference = pd.DataFrame(
        {
            "rank": [1, 2],
            "protein_id": ["A", "B"],
            "gene": ["a", "b"],
            "meta_priority_score": [0.9, 0.5],
            "therapeutic_role": ["bactericidal_candidate", "low_priority_candidate"],
        }
    )
    current = pd.DataFrame(
        {
            "rank": [2, 1, 3],
            "protein_id": ["A", "B", "C"],
            "gene": ["a", "b", "c"],
            "meta_priority_score": [0.8, 0.5, 0.2],
            "therapeutic_role": ["bactericidal_candidate", "low_priority_candidate", "low_priority_candidate"],
        }
    )

    comparison = compare_ranking_snapshots(reference, current, score_tolerance=0.01)
    by_id = comparison.set_index("protein_id")

    assert by_id.loc["A", "change_type"] == "rank_and_score_changed"
    assert by_id.loc["A", "rank_delta"] == 1
    assert by_id.loc["C", "change_type"] == "added"


@pytest.mark.snapshot
@pytest.mark.integration
@pytest.mark.slow
def test_pao1_demo_pipeline_matches_curated_snapshot() -> None:
    reference = PROJECT_ROOT / "tests" / "fixtures" / "ranking_snapshots" / "pao1_demo_reference.csv"
    workspace = PROJECT_ROOT / "data_sessions" / "pseudomonas_aeruginosa_pao1"
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "ranking_snapshot_reference.csv").write_text(reference.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "run_pipeline.py",
            "--organism",
            "Pseudomonas aeruginosa",
            "--strain",
            "PAO1",
            "--allow-demo-data",
            "--mode",
            "compare",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    comparison_path = results_dir / "ranking_snapshot_comparison.csv"
    assert comparison_path.exists()
    comparison = pd.read_csv(comparison_path)
    assert set(comparison["change_type"]) == {"unchanged"}
    assert comparison["max_score_delta"].max() <= 1.0e-6
