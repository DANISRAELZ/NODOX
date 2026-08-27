from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales import phase3_evidence, scoring
from src.nodos_funcionales.host_similarity_semantics import (
    continuous_host_similarity_risk,
    install_phase3_host_similarity_semantics,
)

pytestmark = pytest.mark.unit


def test_phase3_reuses_phase2_continuous_human_similarity_score() -> None:
    features = pd.DataFrame(
        {
            "human_homolog": [1, 1, 0],
            "human_similarity_score": [0.19, 0.88, 0.0],
            # These host-annotation values must remain separate from sequence risk.
            "domain_overlap_score": [0.95, 0.10, 0.70],
            "host_criticality_penalty": [0.90, 0.20, 0.60],
        }
    )

    risk = continuous_host_similarity_risk(features)

    assert risk.tolist() == pytest.approx([0.19, 0.88, 0.0])
    assert features["human_homolog"].tolist() == [1, 1, 0]


def test_install_rebinds_phase3_risk_without_changing_detection_field() -> None:
    install_phase3_host_similarity_semantics()
    features = pd.DataFrame(
        {
            "human_homolog": [1],
            "human_similarity_score": [0.23],
            "domain_overlap_score": [1.0],
            "host_criticality_penalty": [1.0],
        }
    )

    risk = scoring._compute_host_similarity_risk(features)

    assert risk.iloc[0] == pytest.approx(0.23)
    assert features.loc[0, "human_homolog"] == 1


def test_human_homolog_detection_is_audited_but_not_double_counted_as_negative() -> None:
    install_phase3_host_similarity_semantics()
    human_detection = next(
        item
        for item in phase3_evidence.LAYER_VARIABLES
        if item.layer_name == "human_homologs" and item.variable_name == "human_homolog"
    )
    similarity_risk = next(
        item
        for item in phase3_evidence.LAYER_VARIABLES
        if item.layer_name == "human_homologs" and item.variable_name == "host_similarity_risk"
    )

    assert human_detection.negative_high is False
    assert similarity_risk.negative_high is True


def test_phase3_audit_counts_only_high_continuous_risk_as_negative() -> None:
    install_phase3_host_similarity_semantics()
    features = pd.DataFrame(
        {
            "protein_id": ["LOCAL_HIT", "EXTENSIVE_HIT"],
            "gene": ["local", "extensive"],
            "human_homolog": [1, 1],
            "host_similarity_risk": [0.25, 0.92],
            "homology_database": ["computed_diamond_human_homology_v1"] * 2,
        }
    )

    audit = phase3_evidence.build_layer_evidence_audit(features, {})
    human = audit.loc[audit["layer_name"] == "human_homologs"].copy()

    detection = human.loc[human["variable_name"] == "human_homolog"]
    risk = human.loc[human["variable_name"] == "host_similarity_risk"]
    assert detection["evidence_is_negative"].tolist() == [False, False]
    assert risk["evidence_is_negative"].tolist() == [False, True]
