# Theory Alignment Audit

## Proposito

Este documento audita el repositorio frente a la Teoria de Nodos Funcionales.
La cadena conceptual exigida es:

```text
Teoria de Nodos Funcionales
-> postulados
-> preguntas biologicas
-> capas computacionales
-> variables
-> scores parciales
-> scores integradores
-> ranking explicable
-> auditoria, procedencia y limites de interpretacion
```

El diagnostico distingue implementacion real, cobertura parcial y riesgos de
desacoplamiento. No interpreta datos demo, proxy o faltantes como evidencia
biologica negativa.

## Resumen ejecutivo

El proyecto ya contiene una arquitectura modular compatible con la teoria:
validacion, normalizacion, integracion, scoring, reporting, resolucion por
capa, proveedores online opcionales, snapshots curados, auditorias de evidencia
y una capa evolutiva. La principal brecha no es estructural, sino de
alineacion explicita: varias variables teoricas existen con nombres historicos
o en reportes parciales, pero no siempre aparecen como conceptos de la teoria
en los CSV principales, explicaciones simples o documentos de mapeo.

Riesgos principales:

- `meta_priority_score` todavia puede leerse como ranking computacional si no se
  acompana de tipologia, procedencia, confianza y limites de interpretacion.
- La capa evolutiva existe, pero debe exponerse como eje teorico central en
  todos los outputs principales.
- Faltan alias estables para `selectivity_score`, `clinical_context_score`,
  `confidence_modifier`, `functional_node_types` e `interpretation_warning`.
- La jerarquia de evidencia existe por partes, pero necesita una documentacion
  formal y una salida agregada por candidato.
- Algunas referencias demo/snapshot de organismos concretos deben quedar
  explicadas como ejemplos y no como acoplamiento conceptual.

## Auditoria por archivo

| Archivo | Funcion dentro del proyecto | Relacion actual con la teoria | Postulados cubiertos | Postulados no cubiertos o parciales | Variables teoricas presentes | Variables teoricas ausentes o alias faltantes | Riesgos de desacoplamiento | Recomendaciones |
|---|---|---|---|---|---|---|---|---|
| `run_pipeline.py` | Entrada ejecutable del pipeline. | Orquesta el flujo, pero no explicita la cadena teoria -> software. | 2, 6 | 1, 3, 4, 5 solo indirectos | modo, organismo, strain | no aplica | Puede parecer una herramienta de ranking generica. | Documentar que invoca una operacionalizacion teorica. |
| `src/nodos_funcionales/pipeline.py` | Orquestacion validacion -> normalizacion -> integracion -> scoring -> reporting. | Respeta arquitectura modular. | 2, 6 | No declara postulados ni tipologia. | phase2, phase3, sensitivity | no aplica | La secuencia tecnica no muestra la secuencia conceptual. | Mantener; reforzar docs y reportes. |
| `src/nodos_funcionales/layer_registry.py` | Registro de capas resolubles. | Representa capas biologicas y procedencia. | 2, 6 | Tipologia de nodos no explicitada. | essentiality, virulence, functional_network, evolutionary_escape_risk, evidence_quality | capa `evidence_integration` como concepto formal | Si se agregan fuentes fuera del resolver, se rompe trazabilidad. | Preservar contrato; mapear capas a postulados. |
| `src/nodos_funcionales/layer_resolver.py` | Resuelve datos desde usuario, cache, external, proxy. | Base fuerte para procedencia. | 6 | Jerarquia teorica no expuesta en outputs agregados. | source_type, source_name, confidence, retrieval_status | provenance_status agregado por variable | El usuario puede no distinguir proxy/controlado/real. | Consolidar jerarquia de evidencia en docs y CSV. |
| `src/nodos_funcionales/validation.py` | Valida datasets y rangos. | Evita entradas ambiguas y soporta reproducibilidad. | 6 | No explica postulados. | columnas evolutivas, rango 0-1 | estados agregados de evidencia | Faltantes podrian confundirse con negativos si no se reportan. | Mantener distincion missing/insufficient. |
| `src/nodos_funcionales/normalization.py` | Normaliza IDs y tablas. | Permite multi-organismo y comparabilidad. | 2, 6 | Tipologia no calculada aqui. | protein_id_canonical, mapping_confidence | candidate_id alias estable | Si IDs se leen como organismo-especificos, baja generalidad. | Exponer `candidate_id` como alias compatible. |
| `src/nodos_funcionales/integration.py` | Integra capas en `integrated_nodes.csv`. | Une evidencia multicapa antes de scoring. | 1, 2, 3, 4, 5, 6 | Procedencia por variable aun parcial para algunos campos historicos. | virulence_score, host_damage_score, infection_context_score, evolutionary variables, layer provenance | product, aggregate evidence_level, provenance_status | Puede ocultar si un valor es proxy o controlado. | Propagar alias teoricos y mantener columnas legacy. |
| `src/nodos_funcionales/scoring.py` | Calcula features, scores, roles, sensibilidad. | Es el nucleo de operacionalizacion. | 1, 2, 3, 4, 5, 6 | Faltan alias teoricos y tipologia completa en outputs principales. | functional_node_score, antibiotic_target_score, antivirulence_target_score, host_safety_score, evolutionary_robustness_score, confidence fields | selectivity_score, clinical_context_score, confidence_modifier, functional_node_types, interpretation_warning | El score puede parecer opaco si no se descompone por teoria. | Agregar alias, tipologia, advertencias y pruebas. |
| `src/nodos_funcionales/scoring_components.py` | Scores parciales y estrategia preferida. | Descompone estrategias terapeuticas. | 2, 3, 4 | Eje evolutivo no entra directamente aqui. | strategy scores, preferred_strategy | no aplica | Separacion entre scoring legacy y teorico puede ser confusa. | Mantener como motor; documentar correspondencia. |
| `src/nodos_funcionales/evolutionary_escape_risk.py` | Calcula riesgo de escape y robustez evolutiva. | Implementa eje vital de la teoria. | 5, 6 | Movilidad/HGT/recombinacion pueden llegar como unknown o insuficientes. | evolutionary_escape_risk_score, evolutionary_robustness_score, mutation_tolerance_score, evolutionary_constraint_score | mobile_context, hgt_context, recombination_context, resistance_association en outputs principales | Si faltan datos, riesgo bajo no debe inferirse. | Exponer variables y advertencias en scoring/reportes. |
| `src/nodos_funcionales/evolutionary_escape.py` | Capa evolutiva Phase 3 complementaria. | Refuerza restriccion evolutiva y espacio de escape. | 5 | Solo activa en Phase 3 para algunas variables. | mutational_tolerance_score, fitness_cost_score, compensation_difficulty_score, evolutionary_space_constraint_score | no aplica | Puede parecer decorativa si no se reporta en Phase 2. | Mantener y conectar con mapping teorico. |
| `src/nodos_funcionales/redundancy_analysis.py` | Paralogia, rutas alternativas y redundancia. | Soporta escape y conectividad funcional. | 1, 5 | Requiere evidencia curada/externa para no sobreinterpretar. | paralog_count, redundancy_penalty, functional_backup_score | pathway_redundancy alias | Redundancia ausente no equivale a no redundancia. | Agregar alias `pathway_redundancy` y advertencias. |
| `src/nodos_funcionales/functional_node_theory.py` | Score teorico Phase 3. | Representa la teoria de nodos funcionales. | 1, 2, 5, 6 | No siempre visible en ranking principal si Phase 3 no esta activo. | functional_node_theory_score, labels | no aplica | El usuario puede priorizar Phase 2 sin ver lectura teorica. | Exponer tipologia y mapeo tambien en Phase 2. |
| `src/nodos_funcionales/reporting.py` | Exporta rankings, auditorias y markdown. | Buen soporte de auditoria, pero falta marco teorico uniforme. | 2, 3, 4, 5, 6 | Postulado 1 y tipologia no aparecen siempre por candidato. | ranking, candidate_audit, evolutionary_audit, provenance_summary | interpretation_warning, functional_node_types en ranking | Reportes largos pueden diluir limites de interpretacion. | Agregar advertencias obligatorias y campos teoricos. |
| `src/nodos_funcionales/user_explanations.py` | Explicaciones simples. | Evita claims fuertes, pero no enumera los diez puntos solicitados. | 2, 6 | 1, 3, 4, 5 parciales | why_prioritized, sources, confidence | node types, evolutionary constraint, interpretation warning | Usuario no tecnico puede no ver limites evolutivos/procedencia. | Ampliar explicaciones sin inventar evidencia. |
| `src/nodos_funcionales/online_sources.py` | Proveedores externos detras del resolver. | Compatible con fuentes opcionales. | 6 | Teoria no explicitada. | source_name, retrieval_status, confidence | provenance_status formal en todas las salidas | Riesgo si futuras fuentes saltan resolver. | Mantener regla: todo proveedor detras de `fetch_layer_external_source`. |
| `src/nodos_funcionales/generic_annotation_import.py` | Importacion generica multi-organismo. | Fuerte soporte multi-organismo y variables evolutivas. | 5, 6 | Depende de insumos locales. | mobile_context, hgt_context, resistance_association, provenance_status | source_version por variable | Podria interpretarse como real externo si es inferido. | Documentar jerarquia y conservar `inferred_proxy`. |
| `src/nodos_funcionales/online_organism_enrichment.py` | Enriquecimiento online opcional. | Soporta online_optional sin obligar red. | 5, 6 | Evidencia general online no reemplaza datos del usuario. | evidence_level, provenance_status, retrieval_mode, cache_status | no aplica | Sobreinterpretar anotacion general como validacion. | Mantener advertencias y modo offline. |
| `src/nodos_funcionales/ranking_snapshots.py` | Snapshots de ranking. | Favorece reproducibilidad. | 6 | Debe distinguir curated_snapshot de cache/demo. | snapshot outputs | provenance_status agregado | Snapshot puede parecer fuente primaria. | Documentar snapshots como evidencia congelada o comparativa. |
| `src/nodos_funcionales/provenance_user_summary.py` | Resumen de procedencia para usuario. | Apoya trazabilidad. | 6 | Jerarquia teorica no formalizada. | user/external/proxy summary | evidence hierarchy labels | Riesgo de mezclar calidad de evidencia y fuente. | Alinear con `docs/evidence_hierarchy.md`. |
| `config/params.yaml` | Pesos y umbrales configurables. | Centraliza scoring. | 2, 3, 4, 5 | Algunos pesos no tienen comentario inline por limitacion YAML simple. | strategy weights, therapeutic weights, evolutionary weights | meta_priority teoria completa aun distribuida | Pesos ocultos si existen defaults en codigo. | Mantener defaults documentados y mapear en docs. |
| `src/nodos_funcionales/config.py` | Defaults de configuracion. | Asegura compatibilidad sin YAML completo. | 2, 5, 6 | Duplicacion con YAML puede desincronizarse. | DEFAULT_CONFIG | no aplica | Cambios de YAML deben reflejarse en defaults. | Actualizar si se agregan pesos nuevos. |
| `docs/functional_nodes_theory_operationalization.md` | Documento teorico-operativo. | Muy alineado, especialmente eje evolutivo. | 1, 2, 3, 4, 5, 6 | No reemplaza mapping formal solicitado. | postulados, variables evolutivas | tabla teoria -> software completa | Puede quedar aislado de outputs. | Crear `theory_to_software_mapping.md`. |
| `docs/data_model.md` | Diccionario de datos. | Ya documenta varias variables teoricas. | 2, 5, 6 | Debe incorporar nuevos alias teoricos. | evolutionary_robustness_score, reduced_evolutionary_space_score | functional_node_types, confidence_modifier | Si no se actualiza, outputs nuevos quedan sin contrato. | Actualizar en fase final. |
| `tests/test_evolutionary_escape_risk.py` | Tests de capa evolutiva. | Cubre riesgo, robustez y penalizacion. | 5 | No cubre todos los alias de salida principal. | escape risk, robustness, status | functional_node_types, interpretation warnings | Tests unitarios no garantizan reportes. | Agregar tests de outputs finales. |
| `tests/test_scoring.py` | Tests de scoring Phase 2. | Buen punto para alinear scores y outputs. | 2, 3, 4, 5, 6 | Tipologia y jerarquia agregada pendientes. | therapeutic_role, context, evolution | selectivity_score, clinical_context_score, confidence_modifier | Puede pasar aunque falten conceptos teoricos en CSV. | Ampliar assertions teoricas. |
| `tests/test_export.py` | Tests de reportes. | Verifica outputs principales. | 6 | Advertencias obligatorias incompletas. | candidate_audit, explanations, role summaries | interpretation_warning en ranking | Puede no detectar sobreinterpretacion. | Agregar checks de advertencias. |
| `tests/test_generic_annotation_import.py` | Tests multi-organismo e importacion generica. | Soporta no acoplamiento y procedencia. | 5, 6 | Jerarquia completa parcial. | missing_input, insufficient_evidence, inferred_proxy | curated_snapshot | Requiere extension para jerarquia. | Agregar tests de jerarquia formal. |
| `data_templates/*.csv` | Plantillas de entrada. | Hacen reproducibles capas opcionales. | 2, 3, 5, 6 | Tipologia no es entrada, debe derivarse. | clinical, therapy, evolution, redundancy | no aplica | Plantillas pueden parecer datos reales. | Documentar demo/template claramente. |
| `results/*` | Outputs generados. | Ya incluyen rankings, auditorias y explicaciones. | 2, 6 | Dependen de si se regeneran despues de cambios. | ranking, scored_nodes, report_phase2 | new theory columns | Outputs viejos pueden no reflejar teoria. | Regenerar demo estable al final si posible. |

## Cobertura por postulado

| Postulado | Estado actual | Evidencia de implementacion | Brecha principal |
|---|---|---|---|
| 1. Integracion funcional del nodo | Parcial a implementado | `functional_network`, `functional_node_score`, `network_centrality`, `pathway_bottleneck_score`, `functional_node_theory_score` | Faltan alias/reportes para degree, betweenness, module_bridge cuando no vienen de STRING u otra fuente. |
| 2. Prioridad terapeutica multicapa | Implementado | `meta_priority_score`, `evidence_confidence_score`, `optional_data_quality_score`, `layer_resolution_summary` | Requiere `confidence_modifier` y explicacion por capas en ranking principal. |
| 3. Impacto patogenico | Implementado parcial | `virulence_score`, `host_damage_score`, `clinical_impact_score`, `infection_context_score`, `antivirulence_target_score` | Persistencia/adaptacion necesitan alias o senales explicitas. |
| 4. Selectividad terapeutica | Implementado parcial | `host_safety_score`, `human_homolog`, `domain_overlap_score`, localization/accessibility | Falta alias `selectivity_score` y salida clara de host risk. |
| 5. Robustez evolutiva | Implementado, necesita exposicion central | `evolutionary_escape_risk_score`, `evolutionary_robustness_score`, `reduced_evolutionary_space_score`, redundancy | Variables como mobile/HGT/recombination/resistance deben aparecer en CSV principales cuando existan. |
| 6. Trazabilidad e incertidumbre | Implementado parcial | layer provenance, retrieval_status, cache_status online, confidence, evidence_quality | Jerarquia formal y warning de no sobreinterpretacion deben estar en reportes simples y tecnicos. |

## Recomendacion de implementacion

1. Agregar alias teoricos compatibles en `scoring.py` sin eliminar columnas
   legacy.
2. Derivar `functional_node_types` como etiquetas multiples transparentes.
3. Exportar `interpretation_warning`, `confidence_modifier`,
   `selectivity_score`, `clinical_context_score` y variables evolutivas
   solicitadas en `scored_nodes.csv`, `ranking_nodos.csv` y auditorias.
4. Actualizar explicaciones simples y reportes tecnicos con limites de
   interpretacion.
5. Crear documentacion formal de mapping, jerarquia de evidencia, capa
   evolutiva, multi-organismo y teoria primero.
6. Agregar tests offline que verifiquen la presencia y coherencia de estos
   conceptos sin depender de consultas online.
