from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "real_user_curated_dataset_validation.md"


def _text() -> str:
    return " ".join(DOC_PATH.read_text(encoding="utf-8").split()).lower()


def test_real_user_curated_dataset_validation_document_exists_and_sets_scope() -> None:
    assert DOC_PATH.exists()
    text = _text()

    for phrase in [
        "datos reales aportados o revisados por el usuario",
        "no convierte esos datos en evidencia externa verificada automaticamente",
        "excluye",
        "validacion clinica",
        "validacion experimental definitiva",
        "cambios en `scoring.py`",
        "nuevos scores",
    ]:
        assert phrase in text


def test_real_user_curated_dataset_validation_documents_minimum_dataset_and_decisions() -> None:
    text = _text()

    for phrase in [
        "`organism`",
        "`strain`",
        "`protein_id`",
        "`gene`",
        "`curator_name`",
        "`curation_date`",
        "`source_type=user_curated`",
        "`provenance`",
        "`curator_notes`",
        "`local_note`",
        "`accepted_for_test`",
        "`needs_revision`",
        "`insufficient_evidence`",
    ]:
        assert phrase in text


def test_real_user_curated_dataset_validation_preserves_interpretation_guards() -> None:
    text = _text()

    for phrase in [
        "no convierte `user_curated` en `external_verified`",
        "no eleva confianza por `pending_review`, `local_note`, `curator_notes` o `include_for_structure_check`",
        "la ausencia de evidencia suficiente no equivale a bajo riesgo",
        "mantiene separados `therapeutic_priority_score` y `evidence_confidence_score`",
        "mezcla `user_curated` con demo, proxy, cache, online o `controlled_reference`",
        "convierte notas locales en doi, literatura verificada o evidencia experimental",
        "no declara utilidad clinica",
        "predictor definitivo",
    ]:
        assert phrase in text


def test_real_user_curated_dataset_validation_uses_existing_command_parameters() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for phrase in [
        "new_user_curated_dataset.ps1 -ProjectId real_user_curated_validation_01",
        "validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\\real_user_curated_validation_01\\manifest.csv",
        "validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\\real_user_curated_validation_01",
        "--validate-user-curated-manifest user_curated_staging\\real_user_curated_validation_01\\manifest.csv --as-user-layer",
        "run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\\real_user_curated_validation_01 -RunPipeline",
        ".\\.venv\\Scripts\\python.exe -m pytest -p no:cacheprovider -m \"not online\" -q",
    ]:
        assert phrase in text

    for invalid_phrase in [
        "-DatasetId real_user_curated_validation_01",
        "external_verified evidence",
    ]:
        assert invalid_phrase not in text
