from __future__ import annotations

import pandas as pd

from src.nodos_funcionales.functional_node_model import FunctionalNodeModel
from src.nodos_funcionales.model_config import FunctionalNodeModelConfig


def _candidates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protein_id": "P2",
                "gene": "b",
                "antibiotic_target_score": 0.80,
                "antivirulence_target_score": 0.20,
                "functional_node_score": 0.70,
                "selectivity_score": 0.90,
                "clinical_context_score": 0.50,
                "infection_site_access_score": 0.60,
                "evidence_quality_score": 0.20,
                "confidence_ceiling": 0.30,
                "evolutionary_escape_risk_score": 0.75,
                "provenance_status": "demo_only",
            },
            {
                "protein_id": "P1",
                "gene": "a",
                "antibiotic_target_score": 0.50,
                "antivirulence_target_score": 0.80,
                "functional_node_score": 0.65,
                "selectivity_score": 0.85,
                "clinical_context_score": 0.60,
                "infection_site_access_score": 0.55,
                "evidence_quality_score": 0.80,
                "confidence_ceiling": 0.70,
                "evolutionary_escape_risk_score": 0.10,
                "provenance_status": "user_curated",
            },
        ]
    )


def test_functional_node_model_initializes_with_default_config() -> None:
    model = FunctionalNodeModel()
    assert isinstance(model.config, FunctionalNodeModelConfig)


def test_model_produces_deterministic_ranking() -> None:
    model = FunctionalNodeModel()
    first = model.score_candidates(_candidates())
    second = model.score_candidates(_candidates().sample(frac=1, random_state=7))
    assert first["protein_id"].tolist() == second["protein_id"].tolist()


def test_priority_and_evidence_confidence_are_separate() -> None:
    scored = FunctionalNodeModel().score_candidates(_candidates())
    assert "therapeutic_priority_score" in scored.columns
    assert "evidence_confidence_score" in scored.columns
    assert not scored["therapeutic_priority_score"].equals(scored["evidence_confidence_score"])


def test_low_evidence_adds_warning_without_validation_claim() -> None:
    scored = FunctionalNodeModel().score_candidates(_candidates())
    low = scored.loc[scored["protein_id"] == "P2"].iloc[0]
    warning = low["interpretation_warning"].lower()
    assert "low evidence confidence" in warning
    assert "not experimental validation" in warning
    assert "prioritized hypothesis" in warning


def test_evolutionary_escape_penalty_marks_risky_candidates() -> None:
    scored = FunctionalNodeModel().score_candidates(_candidates())
    risky = scored.loc[scored["protein_id"] == "P2"].iloc[0]
    assert risky["evolutionary_escape_penalty_applied"] > 0
    assert "evolutionary escape risk" in risky["interpretation_warning"].lower()


def test_interpretation_warning_uses_conservative_language() -> None:
    scored = FunctionalNodeModel().score_candidates(_candidates())
    assert scored["interpretation_warning"].str.contains("candidate functional node").all()
    assert scored["interpretation_warning"].str.contains("not clinical recommendation").all()
