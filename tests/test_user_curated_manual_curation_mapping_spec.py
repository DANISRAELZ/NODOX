from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_manual_curation_mapping_spec.md"


def _text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def _normalized_text() -> str:
    return " ".join(_text().split())


def test_manual_curation_mapping_spec_documents_scope_and_input_columns() -> None:
    assert DOC_PATH.exists()
    text = _normalized_text()

    required_phrases = [
        "user_curated_staging/minimal_user_curated_validation_01/raw_inputs/manual_curation.csv",
        "`organism`",
        "`strain`",
        "`protein_id`",
        "`gene`",
        "`curator_name`",
        "`curation_date`",
        "`curation_decision`",
        "`evidence_summary`",
        "`evidence_status`",
        "`source_database`",
        "`reference_or_note`",
        "`curator_notes`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_documents_decision_table() -> None:
    text = _normalized_text()

    required_phrases = [
        "`evidence_quality`",
        "`literature_support`",
        "`therapeutic_priority_score`",
        "`clinical recommendation`",
        "`requires_controlled_transformation`",
        "`forbidden_direct_mapping`",
        "apoyar interpretacion de confidence, no priority",
        "preservar `reference_or_note`",
        "`manual_curation.csv` nunca debe convertirse directamente en prioridad terapeutica",
        "`manual_curation.csv` nunca debe interpretarse como recomendacion clinica",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_blocks_automatic_confidence_and_scoring() -> None:
    text = _normalized_text()

    required_phrases = [
        "`manual_curation.csv` no es dataset interno aceptado directamente por `import_dataset.py`",
        "No debe forzarse su importacion solo porque exista un CSV",
        "No debe mapearse automaticamente a score",
        "No debe elevar `confidence` sin reglas explicitas",
        "No debe transformar `pending_review` en evidencia fuerte",
        "`evidence_status=pending_review` o `limited` no debe traducirse a alta confianza",
        "`evidence_summary` debe conservarse como explicacion, no como score automatico",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_preserves_manual_evidence_boundaries() -> None:
    text = _normalized_text()

    required_phrases = [
        "No debe transformar notas locales en literatura verificada",
        "Una nota local debe marcarse como `local_note` o `pending_reference`",
        "una referencia debe tener identificador trazable",
        "No debe transformar `include_for_structure_check` en validacion biologica",
        "`curation_decision=include_for_structure_check` no significa evidencia experimental",
        "Evidencia pendiente no significa evidencia negativa",
        "Ausencia de evidencia no significa bajo riesgo",
        "Evidencia manual no significa evidencia experimental",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_preserves_required_fields_and_separation() -> None:
    text = _normalized_text()

    required_phrases = [
        "Debe preservar `organism`",
        "Debe preservar `strain`",
        "Debe preservar `protein_id`",
        "Debe preservar `gene`",
        "Debe preservar `curator_name`",
        "Debe preservar `curation_date`",
        "Debe preservar `curation_decision`",
        "Debe preservar `evidence_summary`",
        "Debe preservar `evidence_status`",
        "Debe preservar `source_database`",
        "Debe preservar `reference_or_note`",
        "Debe preservar `curator_notes`",
        "Debe conservar `source_type=user_curated`",
        "Debe distinguir `evidence_summary`, `evidence_status`, `curator_notes` y `reference_or_note`",
        "Debe mantener separacion entre `therapeutic_priority_score` y `evidence_confidence_score`",
        "Debe mantener separacion entre evidencia curada e inferencia automatica",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_keeps_source_boundaries_and_multiorganism_design() -> None:
    text = _normalized_text()

    required_phrases = [
        "`user_curated` no equivale a `demo`",
        "`user_curated` no equivale a `proxy`",
        "`user_curated` no equivale a `cache`",
        "`user_curated` no equivale a `controlled_reference`",
        "No se introducen defaults de PAO1, H37Rv ni Corynebacterium",
        "El sistema sigue siendo multi-organismo y theory-first",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_documents_no_execution_or_mutation_guards() -> None:
    text = _normalized_text()

    required_phrases = [
        "no implementa transformacion",
        "no ejecuta importaciones nuevas",
        "no ejecuta scoring",
        "no ejecuta `run_pipeline.py`",
        "no ejecuta modo online",
        "no genera ranking terapeutico",
        "no modifica `src/nodos_funcionales/scoring.py`",
        "no modifica `import_dataset.py`",
        "no modifica `run_pipeline.py`",
        "no modifica snapshots",
        "no modifica `results/`",
        "no modifica `data_processed/`",
        "no modifica `data_sessions/`",
        "no modifica `config/taxon_resolution_cache.json`",
        "no toca ni versiona `user_curated_staging/`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_mapping_spec_documents_future_acceptance_criteria() -> None:
    text = _normalized_text()

    required_phrases = [
        "Tiene funcion pura separada",
        "Tiene prueba unitaria",
        "Preserva todos los campos criticos o los conserva en notas/provenance",
        "No ejecuta scoring",
        "No ejecuta `run_pipeline.py`",
        "No ejecuta modo online",
        "No genera ranking terapeutico",
        "No modifica `src/nodos_funcionales/scoring.py`",
        "No modifica `import_dataset.py` salvo justificacion explicita",
        "No modifica snapshots",
        "No modifica `results/`",
        "No modifica `data_processed/`",
        "No modifica `user_curated_staging/`",
        "No versiona `data_sessions/`",
        "Diferencia `evidence_quality` de `literature_support`",
        "No convierte `pending_review` en high confidence",
        "No convierte `local_note` en DOI o literatura verificada",
        "No interpreta `include_for_structure_check` como validacion experimental",
        "Conserva `organism`/`strain` sin usar defaults",
        "Pasa la suite offline",
    ]

    for phrase in required_phrases:
        assert phrase in text
