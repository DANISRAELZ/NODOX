from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import build_simple_candidate_explanations


pytestmark = pytest.mark.unit


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "protein_id": "GENERIC_A",
        "gene": "geneA",
        "therapeutic_role": "bactericidal_candidate",
        "functional_node_types": "generic_functional_node",
        "therapeutic_priority_score": 0.80,
        "evidence_confidence_score": 0.80,
        "provenance_status": "user_curated",
        "confidence_source_class": "user_curated",
        "optional_data_source_summary": "user_curated=minimal_fixture",
        "retrieval_mode": "local_user_layer",
        "cache_status": "not_cached",
        "data_realism_flag": "user_curated",
    }
    row.update(overrides)
    return row


def _interpretation(**overrides: object) -> str:
    explanations = build_simple_candidate_explanations(pd.DataFrame([_base_row(**overrides)]))
    row = explanations.iloc[0]
    return "\n".join(str(row[column]) for column in explanations.columns).lower()


def test_high_priority_low_confidence_is_flagged_as_fragile_hypothesis() -> None:
    text = _interpretation(therapeutic_priority_score=0.85, evidence_confidence_score=0.30)

    assert "prioridad alta/confianza baja" in text
    assert "hipotesis potencialmente interesante" in text
    assert "evidencia limitada" in text
    assert "no debe presentarse como candidato confirmado" in text
    assert "therapeutic_priority_score" in text
    assert "evidence_confidence_score" in text
    assert "dimensiones distintas" in text


def test_high_priority_high_confidence_still_requires_experimental_validation() -> None:
    text = _interpretation(therapeutic_priority_score=0.82, evidence_confidence_score=0.78)

    assert "prioridad alta/confianza alta" in text
    assert "respaldo relativamente fuerte" in text
    assert "requiere validacion experimental" in text
    assert "no una herramienta clinica ni predictor definitivo" in text


def test_low_priority_high_confidence_is_not_high_therapeutic_priority() -> None:
    text = _interpretation(therapeutic_priority_score=0.25, evidence_confidence_score=0.82)

    assert "prioridad baja/confianza alta" in text
    assert "no respalda automaticamente una prioridad terapeutica alta" in text
    assert "confianza alta no equivale automaticamente a prioridad terapeutica alta" in text


def test_low_priority_low_confidence_is_insufficient_not_negative_evidence() -> None:
    text = _interpretation(therapeutic_priority_score=0.20, evidence_confidence_score=0.25)

    assert "prioridad baja/confianza baja" in text
    assert "prioridad e informacion insuficientes" in text
    assert "no debe sobreinterpretarse" in text
    assert "evidencia insuficiente no equivale a bajo riesgo" in text or "no equivalen a evidencia negativa ni a bajo riesgo" in text


def test_missing_confidence_score_is_not_interpreted_as_high_confidence() -> None:
    text = _interpretation(evidence_confidence_score=None)

    assert "confianza=not_evaluated" in text
    assert "no debe interpretarse como confianza alta ni baja" in text
    assert "evidencia insuficiente no equivale a bajo riesgo" in text


def test_missing_evolutionary_evidence_is_not_low_risk() -> None:
    text = _interpretation(
        evolutionary_escape_risk_status="insufficient",
        evolutionary_escape_risk_interpretation="not_assessed",
    )

    assert "riesgo evolutivo incierto" in text
    assert "no equivale a bajo riesgo" in text
    assert "no sustituye funcionalidad, selectividad, accesibilidad, confianza, evidencia ni validacion experimental" in text


def test_user_curated_remains_separate_from_demo_proxy_cache_and_controlled_reference() -> None:
    text = _interpretation(
        provenance_status="user_curated",
        optional_data_source_summary="demo=absent; proxy=absent; cache=not_primary; controlled_reference=absent",
    )

    assert "user_curated" in text
    assert "demo/proxy/cache no deben presentarse como evidencia real equivalente" in text
    assert "controlled_reference es referencia controlada, no evidencia de usuario" in text
    assert "plataforma multiorganismo" in text
    assert "generic_a" in text
    assert "corynebacterium" not in text
    assert "pao1" not in text
    assert "h37rv" not in text
