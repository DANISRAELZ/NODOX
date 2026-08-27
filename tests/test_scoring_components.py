from __future__ import annotations

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


def _diamond_row(
    *,
    human_homolog: object = 1,
    pident: object = 30.0,
    qcov: object = 0.5,
    scov: object = 0.5,
    evalue: object = 1.0e-20,
    tier: str = "partial_human_sequence_similarity",
) -> pd.Series:
    return pd.Series(
        {
            "human_homolog": human_homolog,
            "percent_identity": pident,
            "query_coverage": qcov,
            "subject_coverage": scov,
            "evalue": evalue,
            "homology_evidence_tier": tier,
        }
    )


def test_human_similarity_score_separates_hit_detection_from_risk() -> None:
    no_hit = _diamond_row(
        human_homolog=0,
        pident=pd.NA,
        qcov=pd.NA,
        scov=pd.NA,
        evalue=pd.NA,
        tier="no_detectable_human_similarity",
    )
    unresolved = _diamond_row(
        human_homolog=pd.NA,
        pident=pd.NA,
        qcov=pd.NA,
        scov=pd.NA,
        evalue=pd.NA,
        tier="diamond_unresolved",
    )

    assert human_similarity_score(no_hit, 0.50) == pytest.approx(0.0)
    assert human_similarity_score(unresolved, 0.50) == pytest.approx(0.50)


def test_local_partial_alignment_is_not_automatic_maximal_host_risk() -> None:
    # Synthetic profile matching the scale of a significant local alignment:
    # modest identity and limited two-sided coverage despite a small e-value.
    partial_local = _diamond_row(
        pident=25.6,
        qcov=0.369,
        scov=0.298,
        evalue=1.16e-12,
        tier="partial_human_sequence_similarity",
    )

    score = human_similarity_score(partial_local, 0.50)

    assert 0.0 < score < 0.50
    assert score != pytest.approx(1.0)


def test_alignment_extent_increases_host_similarity_risk() -> None:
    low_coverage = _diamond_row(
        pident=30.0,
        qcov=0.25,
        scov=0.20,
        evalue=1.0e-25,
    )
    high_coverage = _diamond_row(
        pident=30.0,
        qcov=0.90,
        scov=0.85,
        evalue=1.0e-25,
    )

    assert human_similarity_score(high_coverage, 0.50) > human_similarity_score(low_coverage, 0.50)


def test_identity_increases_host_similarity_risk_at_fixed_coverage() -> None:
    low_identity = _diamond_row(
        pident=22.0,
        qcov=0.80,
        scov=0.80,
        evalue=1.0e-30,
    )
    high_identity = _diamond_row(
        pident=60.0,
        qcov=0.80,
        scov=0.80,
        evalue=1.0e-30,
        tier="strong_human_sequence_homology",
    )

    assert human_similarity_score(high_identity, 0.50) > human_similarity_score(low_identity, 0.50)


def test_tiny_evalue_does_not_override_low_identity_and_local_coverage() -> None:
    local_domain = _diamond_row(
        pident=22.0,
        qcov=0.20,
        scov=0.20,
        evalue=1.0e-100,
        tier="strong_human_sequence_homology",
    )

    score = human_similarity_score(local_domain, 0.50)

    assert score < 0.50


def test_extensive_high_identity_alignment_can_reach_high_risk() -> None:
    extensive = _diamond_row(
        pident=60.0,
        qcov=0.95,
        scov=0.90,
        evalue=1.0e-80,
        tier="strong_human_sequence_homology",
    )

    assert human_similarity_score(extensive, 0.50) > 0.90


def test_coverage_accepts_percent_form_for_legacy_inputs() -> None:
    fractional = _diamond_row(qcov=0.80, scov=0.70)
    percent = _diamond_row(qcov=80.0, scov=70.0)

    assert human_similarity_score(fractional, 0.50) == pytest.approx(
        human_similarity_score(percent, 0.50)
    )


def test_missing_alignment_dimensions_remain_neutral() -> None:
    incomplete = _diamond_row(
        human_homolog=1,
        pident=30.0,
        qcov=pd.NA,
        scov=pd.NA,
        evalue=1.0e-20,
    )

    assert human_similarity_score(incomplete, 0.50) == pytest.approx(0.50)
