from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.ranking_snapshots import build_ranking_snapshot, compare_ranking_snapshots

pytestmark = pytest.mark.unit


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
