from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_minimal_layer_compatibility_map.md"


def test_user_curated_minimal_layer_compatibility_map_documents_table_contract() -> None:
    assert DOC_PATH.exists()

    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "| Archivo local | Corresponde directamente a dataset interno aceptado | Dataset interno sugerido | Estado | Motivo | Precauciones |",
        "`raw_inputs/evolutionary_escape_risk.csv`",
        "`raw_inputs/gene_list.csv`",
        "`raw_inputs/manual_curation.csv`",
        "`raw_inputs/functional_annotations.csv`",
        "`raw_inputs/conservation.csv`",
        "`already_validated`",
        "`not_importable_as_dataset`",
        "`requires_mapping`",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_evolutionary_escape_risk_is_documented_as_already_validated_importable_layer() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "`raw_inputs/evolutionary_escape_risk.csv` | Si | `evolutionary_escape_risk` | `already_validated`",
        "Ya fue importado como primera capa `user_curated`",
        "usando `--as-user-layer`",
        "dataset interno existe en `import_dataset.py`",
        "`evolutionary_escape_risk` es modulador de riesgo, no certeza clinica",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_non_importable_or_ambiguous_local_layers_require_mapping() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "`gene_list` no esta entre datasets internos aceptados",
        "`raw_inputs/gene_list.csv` | No | Ninguno directo | `not_importable_as_dataset`",
        "Usar como inventario de candidatos o insumo previo",
        "`raw_inputs/manual_curation.csv` | No | Conceptualmente podria informar `literature_support`, `evidence_quality` o notas interpretativas | `requires_mapping`",
        "debe conservarse como evidencia revisada o curada, no como score automatico",
        "`raw_inputs/functional_annotations.csv` | No | Conceptualmente podria informar `functional_network`, `contextual_essentiality`, `literature_support` o anotacion auxiliar | `requires_mapping`",
        "anotacion funcional no equivale a evidencia experimental directa",
        "`raw_inputs/conservation.csv` | No | Conceptualmente podria informar `strain_conservation` o `redundancy` | `requires_mapping`",
        "No asumir automaticamente que `conservation.csv` equivale a `strain_conservation`",
        "requiere transformacion explicita",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_layer_compatibility_map_forbids_forced_imports_and_preserves_boundaries() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "no se deben forzar archivos locales a datasets internos incompatibles solo porque exista un CSV",
        "Cada capa requiere mapeo explicito antes de importarse",
        "No debe forzarse una importacion solo porque exista un CSV local",
        "`user_curated` no equivale a `demo`, `proxy`, `cache` ni `controlled_reference`",
        "El mapa preserva esa separacion",
        "Evidencia insuficiente no significa bajo riesgo",
        "`therapeutic_priority_score` y `evidence_confidence_score` siguen separados",
        "`evolutionary_escape_risk` es modulador interpretativo",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_layer_compatibility_map_documents_no_execution_guards() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    required_phrases = [
        "no se ejecutara scoring",
        "no se ejecutara pipeline",
        "no se ejecutara `run_pipeline.py`",
        "no se ejecutara modo online",
        "no se generara ranking terapeutico",
        "no se modificara `src/nodos_funcionales/scoring.py`",
        "no se modificara `run_pipeline.py`",
        "no se modificaran snapshots",
        "no se modificara `results/`",
        "no se modificara `data_processed/`",
        "no se modificara `data_sessions/`",
        "no se modificara `config/taxon_resolution_cache.json`",
        "no se versionara `user_curated_staging/`",
    ]

    for phrase in required_phrases:
        assert phrase in normalized_text


def test_layer_compatibility_map_lists_import_dataset_choices() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for dataset_name in [
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
    ]:
        assert dataset_name in text
