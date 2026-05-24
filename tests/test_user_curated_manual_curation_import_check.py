from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_manual_curation_import_check.md"


def _normalized_text() -> str:
    return " ".join(DOC_PATH.read_text(encoding="utf-8").split())


def test_manual_curation_import_check_documents_scope_and_inputs() -> None:
    assert DOC_PATH.exists()
    text = _normalized_text()

    required_phrases = [
        "importacion controlada de la salida transformada",
        "`manual_curation -> evidence_quality`",
        "La transformacion `manual_curation -> evidence_quality` ya estaba implementada y testeada",
        "Esta fase solo verifico la importacion controlada de la salida transformada",
        "user_curated_staging/minimal_user_curated_validation_01/raw_inputs/manual_curation.csv",
        "user_curated_staging/minimal_user_curated_validation_01/manifest.csv",
        "data_sessions/minimal_user_curated_manual_curation_import_check",
        "El workspace es temporal, local y no debe versionarse como evidencia estable",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_import_check_documents_transformation_and_import_outputs() -> None:
    text = _normalized_text()

    required_phrases = [
        "transform_user_curated_manual_curation_to_evidence_quality",
        "tmp_transformed/evidence_quality.csv",
        "data_user/evidence_quality.csv",
        "data_user/source_exports/evidence_quality.csv",
        "Dataset importado: evidence_quality",
        "Destino como capa de usuario: data_user",
        "Filas fuente: 3; filas mapeadas: 3",
        "verifica que la salida transformada puede importarse como `evidence_quality` `user_curated`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_import_check_documents_traceability() -> None:
    text = _normalized_text()

    required_phrases = [
        "`gene`",
        "`protein_id`",
        "`organism=Example bacterium` dentro de `database`",
        "`strain=minimal_validation_scope` dentro de `database`",
        "`curator_name=Nodos local curator` dentro de `database`",
        "`curation_date=2026-05-24` dentro de `database`",
        "`source_database=user_curated_local_note` dentro de `database`",
        "`source_type=user_curated` dentro de `database`",
        "`curation_decision=include_for_structure_check` dentro de `evidence_notes`",
        "`evidence_summary=...` dentro de `evidence_notes`",
        "`evidence_status=pending_review` dentro de `evidence_notes`",
        "`reference_or_note=Local validation note only` dentro de `evidence_notes`",
        "`curator_notes=...` dentro de `evidence_notes`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_import_check_documents_interpretation_boundaries() -> None:
    text = _normalized_text()

    required_phrases = [
        "sigue siendo `user_curated` o derivada de `user_curated`",
        "No equivale a `demo`, `proxy`, `cache` ni `controlled_reference`",
        "`manual_curation` no equivale automaticamente a prioridad terapeutica",
        "`evidence_quality` apoya interpretacion de evidencia, no ranking terapeutico",
        "`pending_review` no equivale a alta confianza",
        "`evidence_quality_score` y `confidence_ceiling` quedaron como valores conservadores de `0.2`",
        "`include_for_structure_check` no equivale a validacion experimental",
        "`local_note` o `Local validation note only` no equivale a DOI ni literatura verificada",
        "`therapeutic_priority_score` y `evidence_confidence_score` siguen separados",
        "Esta importacion no calcula ni modifica ninguno de esos scores",
        "No se genero ranking ni recomendacion clinica",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_import_check_documents_no_scoring_pipeline_online_or_ranking() -> None:
    text = _normalized_text()

    required_phrases = [
        "no se ejecuto scoring",
        "no se ejecuto `run_pipeline.py`",
        "no se ejecuto modo online",
        "no se genero ranking terapeutico",
        "no se modifico `src/nodos_funcionales/scoring.py`",
        "no se modifico `import_dataset.py`",
        "no se modifico `run_pipeline.py`",
        "no se modificaron snapshots",
        "no se modifico `results/`",
        "no se modifico `data_processed/`",
        "no se modifico `config/taxon_resolution_cache.json` como cambio final",
        "no se modifico ni versiono `user_curated_staging/`",
        "no se versiono `data_sessions/`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_import_check_records_exact_import_command() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert (
        ".\\.venv\\Scripts\\python.exe import_dataset.py --organism \"Example bacterium\" "
        "--strain \"minimal_validation_scope\" --workspace "
        "data_sessions\\minimal_user_curated_manual_curation_import_check "
        "--dataset evidence_quality --input "
        "data_sessions\\minimal_user_curated_manual_curation_import_check\\tmp_transformed\\evidence_quality.csv "
        "--validate-user-curated-manifest "
        "user_curated_staging\\minimal_user_curated_validation_01\\manifest.csv --as-user-layer"
    ) in text
