# Controlled user-curated layer transformation specification

## Proposito

Esta fase define reglas, requisitos y criterios de aceptacion para futuras
transformaciones controladas de capas `user_curated` minimas que no son
importables directamente por `import_dataset.py`.

Esta fase no implementa transformacion todavia. No ejecuta importaciones
nuevas, no ejecuta scoring, no ejecuta `run_pipeline.py`, no genera ranking
terapeutico y no ejecuta modo online.

Paquete local de referencia:

```text
user_curated_staging/minimal_user_curated_validation_01/
```

El paquete local sigue ignorado por Git y `user_curated_staging/` no debe
versionarse.

## Garantias de no modificacion

Esta fase solo define contrato documental. Por lo tanto:

- no modifica `src/nodos_funcionales/scoring.py`;
- no modifica `import_dataset.py`;
- no modifica `run_pipeline.py`;
- no modifica snapshots;
- no modifica `results/`;
- no modifica `data_processed/`;
- no modifica `data_sessions/`;
- no modifica `config/taxon_resolution_cache.json`;
- no versiona `user_curated_staging/`.

## Tabla de transformacion propuesta

| Archivo local | Estado | Dataset interno o destino conceptual | Uso permitido | Requisitos antes de futura transformacion | Prohibiciones y precauciones |
| --- | --- | --- | --- | --- | --- |
| `raw_inputs/gene_list.csv` | `inventory_only` / `requires_candidate_registry_mapping` | Ningun dataset interno directo; `gene_list` no es dataset interno aceptado. | Inventario de candidatos, validacion de IDs, contexto de organismo/cepa y trazabilidad inicial. | `candidate_id`/`protein_id`/`gene`/`locus_tag` consistentes; organismo y cepa explicitos; fuente y estado de evidencia declarados; no mezclar con `demo`, `proxy` ni `cache`. | No debe generar score. No debe convertirse automaticamente en `essentiality`, `virulence`, `functional_network` ni ninguna capa de evidencia. |
| `raw_inputs/manual_curation.csv` | `requires_evidence_mapping` | Posibles destinos conceptuales: `evidence_quality`, `literature_support` o notas interpretativas `user_curated`. | Evidencia revisada o curada; contexto interpretativo trazable. | `curation_decision` controlado; `evidence_summary` no vacio; `evidence_status` explicito; `reference_or_note` trazable; `curator_notes` preservadas; `source_type` o `provenance` compatible con `user_curated`. | No debe transformarse automaticamente en score terapeutico. Debe diferenciar curacion manual de evidencia experimental directa. |
| `raw_inputs/functional_annotations.csv` | `requires_annotation_mapping` | Anotacion auxiliar, contexto funcional, insumo interpretativo o posible mapping futuro a capas especificas si existe regla formal. | Contexto funcional y anotacion auxiliar. | `functional_annotation`/`product_name`/`pathway`/`go_terms`/`ec_number` preservados; `source_database` y `evidence_status` explicitos; distincion entre anotacion predicha, inferida, curada o experimental. | No debe asumirse como `functional_network`. No debe asumirse como `essentiality`. No debe asumirse como `virulence`. No debe interpretarse como evidencia experimental directa. |
| `raw_inputs/conservation.csv` | `requires_conservation_mapping` | Posibles destinos conceptuales: `strain_conservation`; `redundancy` solo si las columnas y semantica lo justifican explicitamente. | Contexto de conservacion con transformacion revisable. | `conservation_scope` definido; `core_genome_presence` interpretado con cuidado; `strain_coverage_score` validado; `allelic_conservation` y `variant_burden` preservados; evidencia incompleta marcada como incertidumbre. | No debe asumirse automaticamente como `strain_conservation`. No debe asumirse automaticamente como baja redundancia o alta restriccion evolutiva. Evidencia incompleta no es bajo riesgo. |
| `raw_inputs/evolutionary_escape_risk.csv` | `direct_import_already_validated` | Dataset interno: `evolutionary_escape_risk`. | Subcapa evolutiva interpretativa ya importada de forma controlada como primera capa `user_curated`. | Preservar campos criticos: `mutation_tolerance_score`, `functional_redundancy_escape_score`, `compensatory_pathway_score`, `fitness_cost_of_escape`, `evolutionary_constraint_score`, `resistance_emergence_risk`, `multi_node_dependency_score`, `confidence`, `notes`. | Mantener como modulador interpretativo del riesgo evolutivo. No equivale a certeza clinica. No debe confundirse con `therapeutic_priority_score`. No debe confundirse con `evidence_confidence_score`. |

## Principios obligatorios

- No forzar importaciones solo porque existe un CSV.
- Ninguna capa local debe convertirse automaticamente en score.
- La transformacion debe ser explicita, revisable y testeada.
- Cada transformacion futura debe preservar `candidate_id`/`gene`/`protein_id`/`organism`/`strain` cuando existan.
- Cada transformacion futura debe preservar `provenance`/`source_type`/`evidence_status`/`confidence`/`notes` cuando existan.
- La ausencia de evidencia no significa bajo riesgo.
- `user_curated` no equivale a `demo`.
- `user_curated` no equivale a `proxy`.
- `user_curated` no equivale a `cache`.
- `user_curated` no equivale a `controlled_reference`.
- `therapeutic_priority_score` y `evidence_confidence_score` deben seguir separados.
- `evolutionary_escape_risk` es modulador interpretativo, no certeza clinica.
- La plataforma prioriza blancos terapeuticos, pero no emite recomendacion clinica.
- El sistema debe conservar orientacion multi-organismo y theory-first.
- No se deben introducir defaults de PAO1, H37Rv ni Corynebacterium.
- `Example bacterium`/`minimal_validation_scope` se usa solo como ejemplo local de validacion.

## Criterios de aceptacion para una futura implementacion

Una transformacion futura solo podra considerarse aceptable si:

1. Tiene documento de mapeo.
2. Tiene prueba unitaria.
3. No degrada `provenance`.
4. No reetiqueta `demo`/`proxy`/`cache` como `user_curated`.
5. No interpreta evidencia faltante como evidencia negativa.
6. No mezcla `confidence` con `priority`.
7. No ejecuta scoring durante importacion.
8. No ejecuta pipeline durante transformacion.
9. Es reversible o al menos auditable.
10. Tiene salida en workspace dedicado.
11. Mantiene separacion entre datos locales ignorados y documentos versionados.
12. Pasa la suite offline.

## Estado de cierre

Estado: especificacion documental de transformaciones controladas creada. La
siguiente fase puede implementar una transformacion minima solo si selecciona
un archivo, documenta el mapeo exacto, agrega prueba unitaria y mantiene la
separacion entre evidencia, confianza, prioridad y procedencia.
