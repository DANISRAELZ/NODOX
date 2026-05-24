from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_conservation_import_check.md"


def test_conservation_import_check_documents_scope_and_inputs() -> None:
    assert DOC_PATH.exists()
    text = " ".join(DOC_PATH.read_text(encoding="utf-8").split())

    required_phrases = [
        "importacion controlada de la salida transformada",
        "`conservation -> strain_conservation`",
        "La transformacion `conservation -> strain_conservation` ya estaba implementada y testeada",
        "Esta fase solo verifico la importacion controlada de la salida transformada",
        "user_curated_staging/minimal_user_curated_validation_01/raw_inputs/conservation.csv",
        "user_curated_staging/minimal_user_curated_validation_01/manifest.csv",
        "data_sessions/minimal_user_curated_conservation_import_check",
        "El workspace es temporal, local y no debe versionarse como evidencia estable",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_conservation_import_check_documents_transformation_and_import_outputs() -> None:
    text = " ".join(DOC_PATH.read_text(encoding="utf-8").split())

    required_phrases = [
        "transform_user_curated_conservation_to_strain_conservation",
        "tmp_transformed/strain_conservation.csv",
        "data_user/strain_conservation.csv",
        "data_user/source_exports/strain_conservation.csv",
        "Dataset importado: strain_conservation",
        "Destino como capa de usuario: data_user",
        "Filas fuente: 3; filas mapeadas: 3",
        "verifica que la salida transformada puede importarse como `strain_conservation` `user_curated`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_conservation_import_check_documents_traceability_and_uncertainty() -> None:
    text = " ".join(DOC_PATH.read_text(encoding="utf-8").split())

    required_phrases = [
        "`gene`",
        "`protein_id`",
        "`organism=Example bacterium` dentro de `database`",
        "`strain=minimal_validation_scope` dentro de `database`",
        "`source_database=user_curated_local_note` dentro de `database`",
        "`source_type=user_curated` dentro de `database`",
        "`evidence_status=pending_review` dentro de `database`",
        "`curator_notes=...` dentro de `database`",
        "incertidumbre como `unknown`, `limited`, `variable`, `moderate`",
        "sin reinterpretarla como bajo riesgo",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_conservation_import_check_documents_no_scoring_pipeline_online_or_ranking() -> None:
    text = " ".join(DOC_PATH.read_text(encoding="utf-8").split())

    required_phrases = [
        "no se ejecuto scoring",
        "no se ejecuto `run_pipeline.py`",
        "no se ejecuto modo online",
        "no se genero ranking terapeutico",
        "no se modifico `src/nodos_funcionales/scoring.py`",
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


def test_conservation_import_check_documents_interpretation_boundaries() -> None:
    text = " ".join(DOC_PATH.read_text(encoding="utf-8").split())

    required_phrases = [
        "sigue siendo `user_curated` o derivada de `user_curated`",
        "No equivale a `demo`, `proxy`, `cache` ni `controlled_reference`",
        "La conservacion no equivale automaticamente a prioridad terapeutica",
        "`core_genome_presence=true` no significa alta prioridad terapeutica",
        "`core_genome_presence=false` no significa bajo riesgo evolutivo",
        "Evidencia incompleta no significa bajo riesgo",
        "`therapeutic_priority_score` y `evidence_confidence_score` siguen separados",
        "Esta importacion no calcula ni modifica ninguno de esos scores",
        "no equivale a evidencia clinica",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_conservation_import_check_records_exact_import_command() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert (
        ".\\.venv\\Scripts\\python.exe import_dataset.py --organism \"Example bacterium\" "
        "--strain \"minimal_validation_scope\" --workspace "
        "data_sessions\\minimal_user_curated_conservation_import_check "
        "--dataset strain_conservation --input "
        "data_sessions\\minimal_user_curated_conservation_import_check\\tmp_transformed\\strain_conservation.csv "
        "--validate-user-curated-manifest "
        "user_curated_staging\\minimal_user_curated_validation_01\\manifest.csv --as-user-layer"
    ) in text
