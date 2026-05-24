from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_minimal_import_check.md"


def test_user_curated_minimal_import_check_documents_dataset_choice() -> None:
    assert DOC_PATH.exists()

    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "`gene_list` no es dataset interno aceptado por `import_dataset.py`",
        "no se forzo `gene_list`",
        "Se eligio `evolutionary_escape_risk`",
        "dataset aceptado",
        "alineado con la subcapa evolutiva",
        "clinical_impact",
        "collateral_sensitivity",
        "contextual_essentiality",
        "curated_disease_context",
        "essentiality",
        "evidence_quality",
        "evolutionary_escape",
        "evolutionary_escape_risk",
        "functional_network",
        "host_annotation",
        "human_homologs",
        "literature_support",
        "localization",
        "redundancy",
        "strain_conservation",
        "therapy_site_context",
        "virulence",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_import_check_documents_local_user_layer_outputs() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "prueba local controlada",
        "data_sessions/minimal_user_curated_validation_01_import_check",
        "data_user/evolutionary_escape_risk.csv",
        "data_user/source_exports/evolutionary_escape_risk.csv",
        "verifica una primera importacion como capa de usuario",
        "`--as-user-layer`",
        "`source_type=user_curated`",
        "`Example bacterium`",
        "`minimal_validation_scope`",
        "No se uso PAO1, H37Rv ni Corynebacterium como default",
        "user_curated_staging/minimal_user_curated_validation_01/",
        "no se versiono `user_curated_staging/`",
        "no se versiono el workspace bajo `data_sessions/`",
        "no debe versionarse como evidencia estable",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_import_check_documents_no_scoring_or_online_execution() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "no se ejecuto scoring",
        "no se ejecuto `run_pipeline.py`",
        "no se produjo ranking terapeutico",
        "no se uso modo online",
        "no se modifico `src/nodos_funcionales/scoring.py`",
        "no se modificaron snapshots",
        "no se modifico `results/`",
        "no se modifico `data_processed/`",
        "no se modifico `config/taxon_resolution_cache.json` como cambio final",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_import_check_documents_interpretation_boundaries() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "`user_curated` no equivale a `demo`, `proxy`, `cache` ni `controlled_reference`",
        "`source_type=user_curated` representa procedencia local revisable",
        "no evidencia clinica",
        "`therapeutic_priority_score` y `evidence_confidence_score` siguen separados",
        "La importacion no calcula ninguno de esos scores",
        "`evolutionary_escape_risk` es modulador interpretativo",
        "no certeza clinica",
        "Evidencia insuficiente no significa bajo riesgo",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_import_check_records_exact_command() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert (
        ".\\.venv\\Scripts\\python.exe import_dataset.py --organism \"Example bacterium\" "
        "--strain \"minimal_validation_scope\" --workspace "
        "data_sessions\\minimal_user_curated_validation_01_import_check "
        "--dataset evolutionary_escape_risk --input "
        "user_curated_staging\\minimal_user_curated_validation_01\\raw_inputs\\evolutionary_escape_risk.csv "
        "--validate-user-curated-manifest "
        "user_curated_staging\\minimal_user_curated_validation_01\\manifest.csv --as-user-layer"
    ) in text
