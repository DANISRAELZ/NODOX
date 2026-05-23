from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import (
    build_simple_candidate_explanations,
    build_simple_candidate_explanations_markdown,
    explain_conservative_interpretation,
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
        "evolutionary_constraint": 0.70,
        "mutation_tolerance": 0.20,
    }
    values.update(overrides)
    return pd.Series(values)


def _text(**overrides: object) -> str:
    return explain_conservative_interpretation(_row(**overrides)).lower()


def test_conservative_mode_does_not_change_scores_or_ranking_fields() -> None:
    ranking = pd.DataFrame([_row(therapeutic_priority_score=0.91, evidence_confidence_score=0.31)])

    explanations = build_simple_candidate_explanations(ranking)

    assert ranking.loc[0, "therapeutic_priority_score"] == 0.91
    assert ranking.loc[0, "evidence_confidence_score"] == 0.31
    assert "conservative_interpretation" in explanations.columns
    text = explanations.loc[0, "conservative_interpretation"].lower()
    assert "no modifica therapeutic_priority_score" in text
    assert "evidence_confidence_score" in text
    assert "pesos ni ranking" in text
    assert "no reordena candidatos" in text


def test_high_score_low_confidence_triggers_conservative_warning() -> None:
    text = _text(therapeutic_priority_score=0.86, evidence_confidence_score=0.30)

    assert "score alto con confianza baja o no evaluada" in text
    assert "evidence_confidence_score bajo" in text
    assert "validacion experimental" in text


def test_missing_confidence_triggers_not_evaluated_warning() -> None:
    text = _text(evidence_confidence_score=None)

    assert "evidence_confidence_score no evaluado" in text
    assert "ausencia o insuficiencia de evidencia no equivale a bajo riesgo" in text


def test_high_or_uncertain_evolutionary_risk_triggers_warning() -> None:
    high_text = _text(evolutionary_escape_risk_score=0.82)
    uncertain_text = _text(evolutionary_escape_risk_score=None, evolutionary_escape_risk_status="insufficient_evidence")

    assert "evolutionary_escape_risk alto" in high_text
    assert "evolutionary_escape_risk no evaluado" in uncertain_text
    assert "riesgo evolutivo ausente, insuficiente o incierto" in uncertain_text
    assert "riesgo evolutivo incierto no equivale a bajo riesgo evolutivo" in uncertain_text


def test_evolutionary_caution_factors_are_reported() -> None:
    text = _text(
        evolutionary_constraint=0.20,
        mutation_tolerance=0.80,
        pathway_redundancy="high",
        paralog_count=3,
        mobile_context="present",
        hgt_context="uncertain",
        recombination_context=True,
        resistance_association="positive",
        evolutionary_escape_risk_missing_variables="mobile_context;hgt_context",
    )

    for phrase in [
        "evolutionary_constraint bajo",
        "mutation_tolerance alta",
        "pathway_redundancy alta",
        "paralog_count alto",
        "mobile_context presente o incierto",
        "hgt_context presente o incierto",
        "recombination_context presente o incierto",
        "resistance_association presente o incierto",
        "evidencia evolutiva insuficiente",
    ]:
        assert phrase in text


def test_source_boundaries_are_conservative() -> None:
    text = _text(
        provenance_status="user_curated",
        confidence_source_class="proxy",
        optional_data_source_summary="demo primary; cache comparison; controlled_reference comparison",
        cache_status="cache_first",
    )

    assert "procedencia demo/proxy/cache limitada" in text
    assert "controlled_reference es referencia controlada, no evidencia de usuario" in text
    assert "user_curated debe leerse segun procedencia trazable" in text
    assert "demo/proxy/cache no son evidencia real equivalente" in text


def test_conservative_markdown_keeps_multiorganism_non_clinical_framing() -> None:
    explanations = build_simple_candidate_explanations(pd.DataFrame([_row()]))
    markdown = build_simple_candidate_explanations_markdown(explanations).lower()

    assert "lectura conservadora" in markdown
    assert "plataforma multiorganismo" in markdown
    assert "no un predictor clinico definitivo" in markdown
    assert "corynebacterium" not in markdown
    assert "pao1" not in markdown
    assert "h37rv" not in markdown
