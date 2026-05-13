from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import (
    THEORY_V3_NOT_ASSESSED_NOTE,
    build_simple_candidate_explanations,
    build_simple_candidate_explanations_markdown,
)

pytestmark = pytest.mark.unit


def test_simple_explanations_mark_demo_and_missing_as_limitations() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "therapeutic_priority_score": [0.71],
            "therapeutic_priority_contribution_summary": [
                "meta_priority_score=0.300; host_safety_score=0.180; host_damage_score=0.100"
            ],
            "top_positive_drivers": ["antibiotic_target_score=0.700"],
            "functional_node_score": [0.68],
            "selectivity_score": [0.72],
            "clinical_context_score": [0.51],
            "evolutionary_robustness_score": [0.61],
            "confidence_modifier": [0.42],
            "essentiality_evidence_state": ["positive"],
            "virulence_evidence_state": ["unknown"],
            "homology_evidence_state": ["negative"],
            "localization_evidence_state": ["positive"],
            "missing_evidence_flags": ["missing_virulence_score"],
            "therapeutic_context_missingness": ["proxy_host_damage_score"],
            "optional_data_source_summary": ["clinical_impact=demo(0.45)"],
            "confidence_source_class": ["proxy"],
            "evidence_level": ["controlled"],
            "provenance_status": ["inferred_proxy"],
            "retrieval_mode": ["controlled_or_proxy"],
            "cache_status": ["not_cached"],
            "data_realism_flag": ["demo_only"],
            "evidence_confidence_score": [0.42],
            "evidence_coverage_score": [0.75],
            "confidence_ceiling": [0.50],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)

    row = explanations.iloc[0]
    assert "bactericidal_candidate" in row["why_prioritized"]
    assert "missing_virulence_score" in row["missing_evidence"]
    assert "no equivalen a evidencia externa real" in row["sources_used"]
    assert "confianza=0.420" in row["confidence_level"]
    assert "meta_priority_score=0.300" in row["therapeutic_priority_components"]
    assert "functional_node_score=0.680" in row["theory_context"]
    assert "provenance_status=inferred_proxy" in row["provenance_context"]


def test_simple_explanations_note_when_theory_score_not_assessed() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "functional_node_theory_score": ["not_assessed"],
            "therapeutic_role_v3": ["antivirulence_candidate"],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)
    markdown = build_simple_candidate_explanations_markdown(explanations)

    assert explanations.loc[0, "theory_v3_assessment_note"] == THEORY_V3_NOT_ASSESSED_NOTE
    assert "Nota theory-first/v3" in markdown
    assert "no equivale a evidencia negativa" in markdown


def test_simple_explanations_note_when_role_v3_not_assessed() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "functional_node_theory_score": [0.72],
            "therapeutic_role_v3": ["not_assessed"],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)

    assert explanations.loc[0, "theory_v3_assessment_note"] == THEORY_V3_NOT_ASSESSED_NOTE


def test_simple_explanations_no_note_when_theory_v3_is_assessed() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "functional_node_theory_score": [0.72],
            "therapeutic_role_v3": ["antivirulence_candidate"],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)
    markdown = build_simple_candidate_explanations_markdown(explanations)

    assert explanations.loc[0, "theory_v3_assessment_note"] == "not_reported"
    assert "Nota theory-first/v3" not in markdown
