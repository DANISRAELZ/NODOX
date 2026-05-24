from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_minimal_validation_release_plan.md"


def test_user_curated_minimal_validation_release_plan_documents_contract() -> None:
    assert DOC_PATH.exists()

    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "`dataset_id` propio y trazable",
        "organismo definido por el usuario",
        "sin asumir PAO1, H37Rv ni Corynebacterium por defecto",
        "candidatos o genes ingresados manualmente",
        "provenance=user_curated",
        "`evidence_confidence_score` explicito",
        "`therapeutic_priority_score` separado de `evidence_confidence_score`",
        "evolutionary_escape_risk",
        "moduladores de riesgo, no como certeza clinica",
        "ausencia o insuficiencia de evidencia no debe interpretarse como bajo riesgo",
        "demo",
        "proxy",
        "cache",
        "controlled_reference",
        "user_curated",
        "no son categorias equivalentes",
        "priorizacion terapeutica exploratoria",
        "no como recomendacion clinica",
        "multi-organismo",
        "theory-first",
        "no modifica `src/nodos_funcionales/scoring.py`",
        "no genera outputs en `results/`",
        "`data_processed/`",
        "`data_sessions/`",
        "`config/taxon_resolution_cache.json`",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_validation_release_plan_keeps_source_types_distinct() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    for source_type in [
        "`demo`",
        "`proxy`",
        "`cache`",
        "`controlled_reference`",
        "`user_curated`",
    ]:
        assert source_type in normalized_text

    forbidden_equivalences = [
        "demo equivale a user_curated",
        "proxy equivale a user_curated",
        "cache equivale a user_curated",
        "controlled_reference equivale a user_curated",
        "demo, proxy, cache, controlled_reference y user_curated son equivalentes",
    ]
    lowered_text = normalized_text.lower()
    for phrase in forbidden_equivalences:
        assert phrase not in lowered_text


def test_user_curated_minimal_validation_release_plan_does_not_allow_default_organism() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()

    forbidden_default_rules = [
        "usar pao1 como default",
        "usar h37rv como default",
        "usar corynebacterium como default",
        "debe rellenarse con pao1",
        "debe rellenarse con h37rv",
        "debe rellenarse con corynebacterium",
        "asignar pao1 automaticamente",
        "asignar h37rv automaticamente",
        "asignar corynebacterium automaticamente",
    ]

    for phrase in forbidden_default_rules:
        assert phrase not in text
