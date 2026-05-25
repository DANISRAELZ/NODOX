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
            "phase3_negative_evidence_summary": ["none"],
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
    assert "evidencia negativa real: none" in row["missing_evidence"]
    assert "Ausencia o insuficiencia no equivale a evidencia negativa ni a bajo riesgo" in row["missing_evidence"]
    assert "no equivalen a evidencia externa real" in row["sources_used"]
    assert "usuario/externa_trazable/snapshot_controlado" in row["sources_used"]
    assert "cache conserva reproducibilidad" in row["sources_used"]
    assert "proxy/demo/controlado solo orientan" in row["sources_used"]
    assert "missing/insufficient indican ausencia o insuficiencia, no evidencia negativa ni bajo riesgo" in row["sources_used"]
    assert "confianza=0.420" in row["confidence_level"]
    assert "independiente_de_prioridad=si" in row["confidence_level"]
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
    assert "hipotesis computacionales" in markdown
    assert "validacion externa" in markdown


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


def test_simple_explanations_include_non_clinical_use_limits() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)
    markdown = build_simple_candidate_explanations_markdown(explanations)
    combined = f"{markdown}\n{explanations.loc[0, 'interpretation_warning']}".lower()

    for phrase in [
        "plataforma de priorizacion terapeutica basada en evidencia",
        "no un predictor clinico definitivo",
        "score alto no equivale a confianza alta",
        "no constituye recomendacion terapeutica",
        "validacion experimental",
        "validacion clinica",
        "evaluacion medica",
        "microbiologica",
        "farmacologica",
        "proxy o evidencia incompleta",
    ]:
        assert phrase in combined


def test_manual_curation_evidence_quality_is_explained_as_user_supplied_not_verified_external() -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["A"],
            "gene": ["geneA"],
            "therapeutic_role": ["bactericidal_candidate"],
            "therapeutic_priority_score": [0.84],
            "evidence_confidence_score": [0.31],
            "evidence_quality_score": [0.20],
            "confidence_ceiling": [0.20],
            "evidence_source_type": ["user_curated_manual_curation"],
            "evidence_notes": [
                "evidence_status=pending_review; "
                "curation_decision=include_for_structure_check; "
                "reference_or_note=Local validation note only; "
                "curator_notes=Preserved local context"
            ],
            "audit_flags": [
                "user_curated;manual_curation;interpretive_only;"
                "limited_confidence;not_experimental_validation;"
                "local_note_not_verified_literature"
            ],
            "phase3_notes": ["manual_curation_interpretive_only; no_clinical_recommendation"],
            "database": [
                "source_database=user_curated_local_note; source_type=user_curated; "
                "organism=Example bacterium; strain=minimal_validation_scope"
            ],
            "provenance_status": ["user_curated"],
            "confidence_source_class": ["user_curated"],
            "optional_data_source_summary": ["user_curated manual_curation"],
            "retrieval_mode": ["local_user_layer"],
            "cache_status": ["not_cached"],
            "data_realism_flag": ["user_curated"],
        }
    )

    explanations = build_simple_candidate_explanations(ranking)
    context = explanations.loc[0, "user_curated_evidence_quality_context"].lower()
    markdown = build_simple_candidate_explanations_markdown(explanations).lower()
    combined = f"{context}\n{markdown}"

    assert "evidencia de usuario o derivada de usuario" in context
    assert "no evidencia externa verificada automaticamente" in context
    assert "`evidence_quality` refleja nivel de evidencia" in context
    assert "no demuestra verdad experimental" in context
    assert "no demuestra verdad experimental, bajo riesgo ni prioridad terapeutica" in context
    assert "pending_review no eleva confianza por si mismo" in context
    assert "include_for_structure_check no es validacion experimental" in context
    assert "local_note no es doi ni literatura verificada" in context
    assert "curator_notes preserva contexto, no prueba externa" in context
    assert "evidence_quality_score=0.200" in context
    assert "confidence_ceiling=0.200" in context
    assert "`therapeutic_priority_score` y `evidence_confidence_score` siguen separados" in context
    assert "contexto user_curated/evidence_quality" in combined
