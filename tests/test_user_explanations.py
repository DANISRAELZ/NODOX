from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import build_simple_candidate_explanations

pytestmark = pytest.mark.unit


def test_simple_explanations_mark_demo_and_missing_as_limitations() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "therapeutic_priority_score": [0.71],
            "top_positive_drivers": ["antibiotic_target_score=0.700"],
            "essentiality_evidence_state": ["positive"],
            "virulence_evidence_state": ["unknown"],
            "homology_evidence_state": ["negative"],
            "localization_evidence_state": ["positive"],
            "missing_evidence_flags": ["missing_virulence_score"],
            "therapeutic_context_missingness": ["proxy_host_damage_score"],
            "optional_data_source_summary": ["clinical_impact=demo(0.45)"],
            "confidence_source_class": ["proxy"],
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
