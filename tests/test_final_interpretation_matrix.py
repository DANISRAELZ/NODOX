from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import (
    build_simple_candidate_explanations,
    build_simple_candidate_explanations_markdown,
    explain_final_interpretation_matrix,
)


pytestmark = pytest.mark.unit


def _row(**overrides: object) -> pd.Series:
    values: dict[str, object] = {
        "protein_id": "GENERIC_NODE",
        "gene": "geneA",
        "therapeutic_role": "bactericidal_candidate",
        "therapeutic_priority_score": 0.82,
        "evidence_confidence_score": 0.82,
        "provenance_status": "user_curated_reviewed_provenance",
        "confidence_source_class": "user_curated",
        "optional_data_source_summary": "user_curated reviewed provenance",
        "retrieval_mode": "local_user_layer",
        "cache_status": "not_cached",
        "data_realism_flag": "user_curated",
        "evolutionary_escape_risk_status": "reviewed",
        "evolutionary_escape_risk_score": 0.20,
        "evolutionary_constraint": 0.80,
        "mutation_tolerance": 0.20,
    }
    values.update(overrides)
    return pd.Series(values)


def _text(**overrides: object) -> str:
    return explain_final_interpretation_matrix(_row(**overrides)).lower()


def test_high_priority_high_confidence_traceable_low_evolutionary_risk_is_strong_for_validation() -> None:
    text = _text()

    assert "final_interpretation_category=strong_candidate_for_experimental_validation" in text
    assert "candidato fuerte para validacion experimental" in text
    assert "no es herramienta clinica ni predictor definitivo" in text
    assert "requiere validacion experimental" in text


def test_high_priority_low_confidence_is_limited_evidence_hypothesis() -> None:
    text = _text(evidence_confidence_score=0.30)

    assert "final_interpretation_category=prioritized_hypothesis_limited_evidence" in text
    assert "evidencia fragil" in text
    assert "no es candidato confirmado" in text


def test_low_priority_high_confidence_is_evidence_supported_but_low_priority() -> None:
    text = _text(therapeutic_priority_score=0.30, evidence_confidence_score=0.82)

    assert "final_interpretation_category=evidence_supported_but_low_priority" in text
    assert "baja prioridad terapeutica bajo el modelo actual" in text
    assert "confianza alta no equivale a prioridad terapeutica alta" in text


def test_low_priority_low_confidence_is_insufficient_information() -> None:
    text = _text(therapeutic_priority_score=0.20, evidence_confidence_score=0.20)

    assert "final_interpretation_category=insufficient_information" in text
    assert "informacion insuficiente" in text
    assert "evidencia insuficiente no equivale a bajo riesgo" in text


def test_missing_confidence_is_not_high_confidence() -> None:
    text = _text(evidence_confidence_score=None)

    assert "confidence=not_reported" in text
    assert "confidence_not_evaluated" in text
    assert "score alto no equivale a confianza alta" in text


def test_evolutionary_risk_high_or_insufficient_adds_evolutionary_caution() -> None:
    high_text = _text(evolutionary_escape_risk_score=0.80)
    missing_text = _text(evolutionary_escape_risk_score=None, evolutionary_escape_risk_status="insufficient")

    assert "secondary_notes=evolutionary_caution" in high_text
    assert "evolutionary_escape_risk=0.800" in high_text
    assert "evolutionary_caution" in missing_text
    assert "riesgo evolutivo incierto no equivale a bajo riesgo evolutivo" in missing_text


def test_mobile_hgt_recombination_or_resistance_context_adds_evolutionary_caution() -> None:
    text = _text(
        mobile_context="present",
        hgt_context="uncertain",
        recombination_context=True,
        resistance_association="positive",
    )

    assert "evolutionary_caution" in text
    assert "mobile_context presente o incierto" in text
    assert "hgt_context presente o incierto" in text
    assert "recombination_context presente o incierto" in text
    assert "resistance_association presente o incierto" in text


def test_demo_proxy_cache_and_controlled_reference_limit_provenance() -> None:
    text = _text(
        provenance_status="proxy",
        confidence_source_class="demo",
        optional_data_source_summary="cache comparison; controlled_reference fixture",
        cache_status="cache_first",
    )

    assert "provenance_limited_interpretation" in text
    assert "demo/proxy/cache no equivalen a evidencia real" in text
    assert "controlled_reference no es evidencia de usuario" in text


def test_user_curated_without_traceability_requires_traceability_note() -> None:
    text = _text(
        provenance_status="user_curated",
        confidence_source_class="user_curated",
        optional_data_source_summary="user_curated",
        retrieval_mode="local_user_layer",
    )

    assert "user_curated_requires_traceability" in text
    assert "user_curated requiere trazabilidad" in text


def test_final_matrix_does_not_modify_scores_and_is_rendered_in_markdown() -> None:
    ranking = pd.DataFrame([_row(therapeutic_priority_score=0.77, evidence_confidence_score=0.33)])

    explanations = build_simple_candidate_explanations(ranking)
    markdown = build_simple_candidate_explanations_markdown(explanations).lower()

    assert ranking.loc[0, "therapeutic_priority_score"] == 0.77
    assert ranking.loc[0, "evidence_confidence_score"] == 0.33
    assert "final_interpretation_matrix" in explanations.columns
    assert "matriz final de interpretacion" in markdown
    assert "matriz final interpretativa: no modifica scores, pesos ni ranking" in markdown
    assert "plataforma multiorganismo" in markdown
    assert "corynebacterium" not in markdown
    assert "pao1" not in markdown
    assert "h37rv" not in markdown
