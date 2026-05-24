from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_minimal_local_package_validation.md"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"


def test_user_curated_minimal_local_package_validation_documents_local_closure() -> None:
    assert DOC_PATH.exists()

    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "user_curated_staging/minimal_user_curated_validation_01/",
        "permanece ignorado por Git",
        "no debe versionarse",
        "`README.md`",
        "`manifest.csv`",
        "`raw_inputs/`",
        "`provenance/`",
        "`notes/`",
        "`gene_list.csv`",
        "`manual_curation.csv`",
        "`functional_annotations.csv`",
        "`conservation.csv`",
        "`evolutionary_escape_risk.csv`",
        "paso validacion por Python",
        "paso validacion por wrapper PowerShell",
        "Esta prevalidacion no ejecuta pipeline, importacion ni scoring",
        "`src/nodos_funcionales/scoring.py`",
        "snapshots",
        "`results/`",
        "`data_processed/`",
        "`data_sessions/`",
        "`config/taxon_resolution_cache.json`",
        "`Example bacterium`",
        "`minimal_validation_scope`",
        "No se uso PAO1, H37Rv ni Corynebacterium como default",
        "candidatos del paquete son ficticios",
        "no constituyen evidencia clinica",
        "`source_type=user_curated`",
        "solo representa estructura local y trazabilidad revisable",
        "`therapeutic_priority_score` y `evidence_confidence_score` deben permanecer separados",
        "Evidencia insuficiente no significa bajo riesgo",
        "`evolutionary_escape_risk` actua como modulador interpretativo",
        "no como certeza clinica",
        "`demo`, `proxy`, `cache`, `controlled_reference` y `user_curated` no son equivalentes",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_user_curated_minimal_local_package_validation_records_manifest_commands() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert (
        ".\\.venv\\Scripts\\python.exe scripts\\validate_user_curated_manifest.py "
        "user_curated_staging\\minimal_user_curated_validation_01\\manifest.csv"
    ) in text
    assert (
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\validate_user_curated_manifest.ps1 "
        "-ManifestPath user_curated_staging\\minimal_user_curated_validation_01\\manifest.csv"
    ) in text
    assert "[OK] Manifest user_curated valido para revision/importacion." in text
    assert "[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring." in text


def test_user_curated_staging_is_protected_from_versioning() -> None:
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    gitignore_text = GITIGNORE_PATH.read_text(encoding="utf-8")

    documentation_protects_package = (
        "user_curated_staging/" in doc_text
        and "no debe versionarse" in doc_text
    )
    gitignore_protects_package = any(
        line.strip() == "user_curated_staging/"
        for line in gitignore_text.splitlines()
    )

    assert documentation_protects_package or gitignore_protects_package
    assert gitignore_protects_package
