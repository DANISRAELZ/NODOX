from __future__ import annotations

import json

import pandas as pd
import pytest

from src.nodos_funcionales.user_explanations import (
    build_simple_candidate_explanations,
    build_simple_candidate_explanations_markdown,
)


pytestmark = pytest.mark.unit


def _ranking() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protein_id": "GENERIC_A",
                "gene": "geneA",
                "therapeutic_role": "bactericidal_candidate",
                "functional_node_types": "generic_functional_node",
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
            },
            {
                "protein_id": "GENERIC_B",
                "gene": "geneB",
                "therapeutic_role": "mixed_strategy_candidate",
                "functional_node_types": "generic_functional_node",
                "therapeutic_priority_score": 0.79,
                "evidence_confidence_score": 0.30,
                "provenance_status": "user_curated",
                "confidence_source_class": "proxy",
                "optional_data_source_summary": "demo comparison; cache comparison; controlled_reference fixture",
                "retrieval_mode": "local_user_layer",
                "cache_status": "cache_first",
                "data_realism_flag": "user_curated",
                "evolutionary_escape_risk_status": "insufficient",
                "evolutionary_escape_risk_score": None,
                "mobile_context": "present",
                "hgt_context": "uncertain",
                "recombination_context": "present",
                "resistance_association": "positive",
            },
        ]
    )


def test_final_interpretation_matrix_survives_dataframe_markdown_csv_and_json(tmp_path) -> None:
    ranking = _ranking()
    original_order = ranking["protein_id"].tolist()
    original_scores = ranking[["therapeutic_priority_score", "evidence_confidence_score"]].copy()

    explanations = build_simple_candidate_explanations(ranking)
    markdown = build_simple_candidate_explanations_markdown(explanations)
    csv_path = tmp_path / "candidate_explanations_simple.csv"
    json_path = tmp_path / "candidate_explanations_simple.json"
    explanations.to_csv(csv_path, index=False)
    explanations.to_json(json_path, orient="records", force_ascii=False)

    csv_text = csv_path.read_text(encoding="utf-8").lower()
    json_records = json.loads(json_path.read_text(encoding="utf-8"))
    exported_text = f"{markdown}\n{csv_text}\n{json.dumps(json_records, ensure_ascii=False)}".lower()

    assert "final_interpretation_matrix" in explanations.columns
    assert "conservative_interpretation" in explanations.columns
    assert "score_confidence_interpretation" in explanations.columns
    assert "matriz final de interpretacion" in markdown.lower()
    assert "final_interpretation_matrix" in csv_text
    assert "final_interpretation_matrix" in json_records[0]
    assert explanations["protein_id"].tolist() == original_order
    pd.testing.assert_frame_equal(
        ranking[["therapeutic_priority_score", "evidence_confidence_score"]],
        original_scores,
    )

    for phrase in [
        "no es herramienta clinica ni predictor definitivo",
        "validacion experimental",
        "evidencia insuficiente no equivale a bajo riesgo",
        "riesgo evolutivo incierto no equivale a bajo riesgo evolutivo",
        "demo/proxy/cache no equivalen a evidencia real",
        "user_curated requiere trazabilidad",
    ]:
        assert phrase in exported_text

    assert "corynebacterium" not in exported_text
    assert "pao1" not in exported_text
    assert "h37rv" not in exported_text
