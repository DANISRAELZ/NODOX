from __future__ import annotations

from pathlib import Path


FORBIDDEN_ORGANISM_DEFAULTS = {
    "PAO1",
    "H37Rv",
    "Corynebacterium",
    "Pseudomonas aeruginosa",
    "Mycobacterium tuberculosis",
}


def test_user_curated_controlled_scoring_spec_contract() -> None:
    project_root = Path(__file__).resolve().parents[1]
    spec_path = project_root / "docs" / "user_curated_controlled_scoring_spec.md"

    assert spec_path.exists()

    spec_text = spec_path.read_text(encoding="utf-8")
    normalized_text = " ".join(spec_text.split())
    required_terms = {
        "approved_for_controlled_scoring",
        "not_ready_for_scoring",
        "requires_expert_review",
        "conditionally_ready_for_future_controlled_scoring",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "Ausencia de evidencia no equivale a bajo riesgo",
        "No ejecutar scoring sin aprobacion manual",
        "No generar rankings sin revision experta",
        "Datos demo no deben ser usados como evidencia real",
        "Datos proxy no deben equivaler a datos `user_curated`",
        "no equivale a validacion biologica",
        "validacion clinica",
        "validacion experimental",
        "multiorganismo",
        "manifest.csv",
        "dataset_id",
        "placeholders activos",
        "provenance",
        "evidence_status=pending",
        "advertencias evolutivas",
        "high therapeutic_priority_score",
        "low evidence_confidence_score",
        "high evolutionary_escape_risk",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "No evaluable por evidencia insuficiente",
        "No usar cache, demo o proxy como evidencia real",
    }
    for term in required_terms:
        assert term in normalized_text

    for forbidden_default in FORBIDDEN_ORGANISM_DEFAULTS:
        assert forbidden_default not in spec_text
