from __future__ import annotations

import math
import pandas as pd
import pytest

from src.nodos_funcionales.scoring_components import (
    assign_preferred_strategy,
    calculate_legacy_score,
    calculate_meta_priority_score,
    calculate_strategy_scores,
    human_similarity_score,
    validate_scoring_inputs,
)

pytestmark = pytest.mark.unit


def test_component_scores_are_interpretable_and_bounded() -> None:
    features = pd.DataFrame(
        {
            "protein_id": ["A"],
            "essential": [1],
            "virulence_score": [0.8],
            "human_homolog": [0],
            "evalue": [1.0],
            "localization": ["outer_membrane"],
            "essentiality_support": [1.0],
            "virulence_support": [0.8],
            "physical_accessibility": [0.85],
            "host_safety_score": [0.9],
            "conservation_score": [0.7],
            "small_molecule_feasibility": [0.55],
            "low_redundancy_score": [0.8],
            "evidence_confidence_score": [0.75],
            "antibody_feasibility": [0.9],
            "host_damage_reduction_potential": [0.8],
            "network_centrality": [0.7],
            "pathway_bottleneck_score": [0.6],
            "functional_dependency_score": [0.65],
        }
    )
    weights = {
        "legacy": {
            "essentiality": 0.30,
            "virulence": 0.25,
            "no_human_homolog": 0.25,
            "accessibility": 0.15,
            "host_risk": 0.05,
        },
        "antibiotic_target": {
            "essentiality_support": 0.28,
            "host_safety_score": 0.22,
            "conservation_score": 0.18,
            "small_molecule_feasibility": 0.16,
            "low_redundancy_score": 0.10,
            "evidence_confidence_score": 0.06,
        },
        "antivirulence_target": {
            "virulence_support": 0.30,
            "physical_accessibility": 0.18,
            "antibody_feasibility": 0.12,
            "host_damage_reduction_potential": 0.16,
            "host_safety_score": 0.18,
            "evidence_confidence_score": 0.06,
        },
        "functional_node": {
            "network_centrality": 0.26,
            "pathway_bottleneck_score": 0.24,
            "functional_dependency_score": 0.24,
            "low_redundancy_score": 0.18,
            "evidence_confidence_score": 0.08,
        },
        "meta_priority": {
            "antibiotic_target_score": 0.50,
            "antivirulence_target_score": 0.35,
            "functional_node_score": 0.15,
        },
    }

    validate_scoring_inputs(features)
    legacy = calculate_legacy_score(features, weights["legacy"], 0.5, 1.0e-10)
    strategy_scores, contributions = calculate_strategy_scores(features, weights)
    for column, values in strategy_scores.items():
        features[column] = values
        assert values.between(0, 1).all(), column
        assert contributions[column]

    meta, meta_contributions = calculate_meta_priority_score(features, weights["meta_priority"])
    preferred = assign_preferred_strategy(features)

    assert legacy.between(0, 1).all()
    assert meta.between(0, 1).all()
    assert set(meta_contributions) == set(weights["meta_priority"])
    assert preferred.loc[0, "preferred_strategy"] in {
        "antibiotic_target",
        "antivirulence_target",
        "functional_node",
    }


def test_validate_scoring_inputs_reports_missing_columns() -> None:
    with pytest.raises(ValueError, match="faltan columnas requeridas"):
        validate_scoring_inputs(pd.DataFrame({"protein_id": ["A"]}))


@pytest.mark.parametrize(
    ("tier", "evalue", "expected"),
    [
        (
            "partial_human_sequence_similarity",
            2.13e-11,
            0.60,
        ),
        (
            "strong_human_sequence_homology",
            3.90e-23,
            0.70,
        ),
        (
            "strong_human_sequence_homology",
            1.00e-100,
            1.00,
        ),
    ],
)
def test_human_similarity_score_respects_homology_tier_floor(
    tier: str,
    evalue: float,
    expected: float,
) -> None:
    row = pd.Series(
        {
            "human_homolog": 1,
            "evalue": evalue,
            "homology_evidence_tier": tier,
        }
    )

    assert human_similarity_score(
        row,
        neutral_unknown_score=0.50,
    ) == pytest.approx(expected)


def test_human_similarity_score_orders_resolved_states_conservatively() -> None:
    rows = {
        "no_hit": pd.Series(
            {
                "human_homolog": 0,
                "evalue": pd.NA,
                "homology_evidence_tier":
                    "no_detectable_human_similarity",
            }
        ),
        "unresolved": pd.Series(
            {
                "human_homolog": pd.NA,
                "evalue": pd.NA,
                "homology_evidence_tier":
                    "diamond_unresolved",
            }
        ),
        "partial": pd.Series(
            {
                "human_homolog": 1,
                "evalue": 2.13e-11,
                "homology_evidence_tier":
                    "partial_human_sequence_similarity",
            }
        ),
        "strong": pd.Series(
            {
                "human_homolog": 1,
                "evalue": 3.90e-23,
                "homology_evidence_tier":
                    "strong_human_sequence_homology",
            }
        ),
    }

    scores = {
        name: human_similarity_score(
            row,
            neutral_unknown_score=0.50,
        )
        for name, row in rows.items()
    }

    assert scores["no_hit"] == pytest.approx(0.00)
    assert scores["unresolved"] == pytest.approx(0.50)
    assert scores["partial"] == pytest.approx(0.60)
    assert scores["strong"] == pytest.approx(0.70)

    assert (
        scores["no_hit"]
        < scores["unresolved"]
        < scores["partial"]
        < scores["strong"]
    )


def test_human_similarity_score_preserves_legacy_behavior_without_tier() -> None:
    row = pd.Series(
        {
            "human_homolog": 1,
            "evalue": 3.90e-23,
        }
    )

    expected = -math.log10(3.90e-23) / 50.0

    assert human_similarity_score(
        row,
        neutral_unknown_score=0.50,
    ) == pytest.approx(expected)
