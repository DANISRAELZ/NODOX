from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "user_curated_controlled_layer_transformation_spec.md"


def _doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def _normalized_doc_text() -> str:
    return " ".join(_doc_text().split())


def test_controlled_layer_transformation_spec_documents_no_execution_scope() -> None:
    assert DOC_PATH.exists()
    text = _normalized_doc_text()

    required_phrases = [
        "no implementa transformacion todavia",
        "No ejecuta importaciones nuevas",
        "no ejecuta scoring",
        "no ejecuta `run_pipeline.py`",
        "no genera ranking terapeutico",
        "no ejecuta modo online",
        "no modifica `src/nodos_funcionales/scoring.py`",
        "no modifica `import_dataset.py`",
        "no modifica `run_pipeline.py`",
        "no modifica snapshots",
        "no modifica `results/`",
        "no modifica `data_processed/`",
        "no modifica `data_sessions/`",
        "no modifica `config/taxon_resolution_cache.json`",
        "no versiona `user_curated_staging/`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_controlled_layer_transformation_spec_maps_each_local_file_state() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "`raw_inputs/gene_list.csv` | `inventory_only` / `requires_candidate_registry_mapping`",
        "`gene_list` no es dataset interno aceptado",
        "`raw_inputs/manual_curation.csv` | `requires_evidence_mapping`",
        "`raw_inputs/functional_annotations.csv` | `requires_annotation_mapping`",
        "`raw_inputs/conservation.csv` | `requires_conservation_mapping`",
        "`raw_inputs/evolutionary_escape_risk.csv` | `direct_import_already_validated`",
        "Dataset interno: `evolutionary_escape_risk`",
        "ya importada de forma controlada como primera capa `user_curated`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_gene_list_contract_is_inventory_only_not_evidence_layer() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "Inventario de candidatos, validacion de IDs, contexto de organismo/cepa y trazabilidad inicial",
        "`candidate_id`/`protein_id`/`gene`/`locus_tag` consistentes",
        "organismo y cepa explicitos",
        "fuente y estado de evidencia declarados",
        "No debe generar score",
        "No debe convertirse automaticamente en `essentiality`, `virulence`, `functional_network` ni ninguna capa de evidencia",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_manual_curation_contract_requires_evidence_mapping_not_automatic_score() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "Posibles destinos conceptuales: `evidence_quality`, `literature_support` o notas interpretativas `user_curated`",
        "`curation_decision` controlado",
        "`evidence_summary` no vacio",
        "`evidence_status` explicito",
        "`reference_or_note` trazable",
        "`curator_notes` preservadas",
        "`source_type` o `provenance` compatible con `user_curated`",
        "No debe transformarse automaticamente en score terapeutico",
        "Debe diferenciar curacion manual de evidencia experimental directa",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_functional_annotations_contract_requires_annotation_mapping() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "Anotacion auxiliar, contexto funcional, insumo interpretativo o posible mapping futuro",
        "`functional_annotation`/`product_name`/`pathway`/`go_terms`/`ec_number` preservados",
        "`source_database` y `evidence_status` explicitos",
        "distincion entre anotacion predicha, inferida, curada o experimental",
        "No debe asumirse como `functional_network`",
        "No debe asumirse como `essentiality`",
        "No debe asumirse como `virulence`",
        "No debe interpretarse como evidencia experimental directa",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_conservation_contract_requires_explicit_transformation() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "Posibles destinos conceptuales: `strain_conservation`; `redundancy` solo si las columnas y semantica lo justifican explicitamente",
        "`conservation_scope` definido",
        "`core_genome_presence` interpretado con cuidado",
        "`strain_coverage_score` validado",
        "`allelic_conservation` y `variant_burden` preservados",
        "evidencia incompleta marcada como incertidumbre",
        "No debe asumirse automaticamente como `strain_conservation`",
        "No debe asumirse automaticamente como baja redundancia o alta restriccion evolutiva",
        "Evidencia incompleta no es bajo riesgo",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_evolutionary_escape_risk_contract_preserves_interpretive_boundary() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "`mutation_tolerance_score`",
        "`functional_redundancy_escape_score`",
        "`compensatory_pathway_score`",
        "`fitness_cost_of_escape`",
        "`evolutionary_constraint_score`",
        "`resistance_emergence_risk`",
        "`multi_node_dependency_score`",
        "`confidence`",
        "`notes`",
        "Mantener como modulador interpretativo del riesgo evolutivo",
        "No equivale a certeza clinica",
        "No debe confundirse con `therapeutic_priority_score`",
        "No debe confundirse con `evidence_confidence_score`",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_controlled_layer_transformation_spec_documents_scientific_boundaries() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "No forzar importaciones solo porque existe un CSV",
        "Ninguna capa local debe convertirse automaticamente en score",
        "La transformacion debe ser explicita, revisable y testeada",
        "La ausencia de evidencia no significa bajo riesgo",
        "`user_curated` no equivale a `demo`",
        "`user_curated` no equivale a `proxy`",
        "`user_curated` no equivale a `cache`",
        "`user_curated` no equivale a `controlled_reference`",
        "`therapeutic_priority_score` y `evidence_confidence_score` deben seguir separados",
        "`evolutionary_escape_risk` es modulador interpretativo, no certeza clinica",
        "La plataforma prioriza blancos terapeuticos, pero no emite recomendacion clinica",
        "El sistema debe conservar orientacion multi-organismo y theory-first",
        "No se deben introducir defaults de PAO1, H37Rv ni Corynebacterium",
        "`Example bacterium`/`minimal_validation_scope` se usa solo como ejemplo local de validacion",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_future_acceptance_criteria_are_documented() -> None:
    text = _normalized_doc_text()

    required_phrases = [
        "Tiene documento de mapeo",
        "Tiene prueba unitaria",
        "No degrada `provenance`",
        "No reetiqueta `demo`/`proxy`/`cache` como `user_curated`",
        "No interpreta evidencia faltante como evidencia negativa",
        "No mezcla `confidence` con `priority`",
        "No ejecuta scoring durante importacion",
        "No ejecuta pipeline durante transformacion",
        "Es reversible o al menos auditable",
        "Tiene salida en workspace dedicado",
        "Mantiene separacion entre datos locales ignorados y documentos versionados",
        "Pasa la suite offline",
    ]

    for phrase in required_phrases:
        assert phrase in text
