from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_end_to_end_flow.md"


def _doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8").lower()


def test_user_curated_end_to_end_flow_document_exists() -> None:
    assert DOC_PATH.exists()


def test_user_curated_end_to_end_flow_documents_source_boundaries() -> None:
    text = _doc_text()

    assert "user_curated" in text
    assert "procedencia" in text or "provenance" in text
    assert "demo" in text
    assert "proxy" in text
    assert "cache" in text
    assert "controlled_reference" in text
    assert "online" in text or "fuentes online" in text


def test_user_curated_end_to_end_flow_documents_score_interpretation() -> None:
    text = _doc_text()

    assert "therapeutic_priority_score" in text
    assert "evidence_confidence_score" in text
    assert "score terapeutico alto no equivale automaticamente a confianza alta" in text
    assert "confianza alta tampoco significa automaticamente prioridad terapeutica alta" in text
    assert "validacion experimental" in text
    assert "no es una herramienta clinica" in text or "no sustituye validacion experimental" in text


def test_user_curated_end_to_end_flow_documents_conservative_evolutionary_reading() -> None:
    text = _doc_text()

    assert "ausencia o insuficiencia de evidencia no equivale a bajo riesgo" in text
    for term in [
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
        "paralog_count",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
    ]:
        assert term in text


def test_user_curated_end_to_end_flow_documents_multiorganism_orientation() -> None:
    text = _doc_text()

    assert "multiorganismo" in text or "multi-organismo" in text
    assert "cualquier organismo" in text
    assert "no son valores por defecto" in text
    assert "no deben acoplar el flujo" in text
