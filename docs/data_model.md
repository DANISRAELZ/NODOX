# Modelo de datos

## Capa de identificación

- `protein_id_original`
- `protein_id_canonical`
- `protein_id`
- `gene`
- `gene_symbol_normalized`
- `source_database`
- `mapping_confidence`

## Evidencia primaria

- `essential`
- `virulence_factor`
- `virulence_score`
- `human_homolog`
- `evalue`
- `human_gene`
- `localization`

## Estados de evidencia

- `essentiality_evidence_state`
- `virulence_evidence_state`
- `homology_evidence_state`
- `localization_evidence_state`

## Calidad y cobertura

- `essentiality_confidence`
- `virulence_confidence`
- `homology_confidence`
- `localization_confidence`
- `multi_source_support`
- `evidence_coverage_score`
- `evidence_confidence_score`

## Seguridad del hospedero

- `human_similarity_score`
- `domain_overlap_score`
- `off_target_risk_score`
- `host_criticality_penalty`
- `host_safety_score`
- `host_risk_audit_summary`

Cuando `host_annotation` proviene del proveedor InterPro o de un fallback
controlado, tambien pueden viajar columnas de auditoria:

- `interpro_bacterial_accession`
- `interpro_human_accession`
- `interpro_bacterial_entries`
- `interpro_human_entries`
- `interpro_shared_entries`
- `human_essentiality_score`
- `human_essentiality_status`
- `human_essentiality_lookup_status`
- `interpro_rule`
- `interpro_missing_flags`
- `host_annotation_rule`
- `host_annotation_inputs`
- `host_annotation_confidence_reason`
- `host_annotation_missing_flags`

## Tratabilidad

- `physical_accessibility`
- `small_molecule_feasibility`
- `antibody_feasibility`
- `infection_site_access`
- `membrane_crossing_penalty`

## Proxies derivadas con datos disponibles

- `host_damage_reduction_potential`
- `disease_severity_association`
- `clinical_impact_score`
- `host_damage_score`
- `infection_site_access_score`
- `infection_context_score`

Estas columnas pueden acompañarse de banderas `*_is_proxy`.

## Clasificación terapéutica fase 1

- `therapeutic_role`
- `therapeutic_priority_score`
- `therapeutic_role_rule`
- `therapeutic_context_missingness`

## Contexto infeccioso empírico opcional

- `clinical_impact_database`
- `disease_context_database`
- `therapy_site_context_database`

Estas columnas indican si una señal terapéutica sigue siendo proxy o si ya
proviene de una capa contextual cargada por el usuario.

## Capas opcionales ya soportadas

- `network_centrality`
- `pathway_bottleneck_score`
- `redundancy_penalty`
- `functional_dependency_score`
- `core_genome_presence`
- `strain_coverage_score`
- `allelic_conservation`
- `variant_burden`
- `domain_overlap_score`
- `host_criticality_penalty`
- `host_risk_audit_summary`

Estas columnas pueden entrar desde:

- `data_raw/functional_network.csv`
- `data_raw/strain_conservation.csv`
- `data_raw/host_annotation.csv`

## Arquitectura preparada para futuras capas

- `host_damage_reduction_potential`
- `disease_severity_association`
- `clinical_impact_score`

Cuando una capa es placeholder, el dataset incluye una bandera
`*_is_placeholder`.

## Fase 3: teoria de nodos funcionales y robustez evolutiva

La Fase 3 es opcional y esta desactivada por defecto en `config/params.yaml`.
Los campos siguientes preparan el modelo de datos, pero no cambian todavia el
ranking principal ni los scores de Fase 1/Fase 2.

Las fuentes esperadas son CSV opcionales en `data_raw/`, `data_user/`,
`data_cache/` o `data_external/`, usando las plantillas:

- `data_templates/contextual_essentiality_template.csv`
- `data_templates/evolutionary_escape_template.csv`
- `data_templates/evolutionary_escape_risk_template.csv`
- `data_templates/collateral_sensitivity_template.csv`
- `data_templates/evidence_quality_template.csv`

### Campos de teoria

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `contextual_essentiality_score` | numerico | 0-1 o faltante controlado | score | evidencia curada de nicho, infeccion, Tn-seq contextual o literatura | Alto indica que el nodo parece importante en el contexto real de infeccion. |
| `pleiotropy_score` | numerico | 0-1 o faltante controlado | score | red funcional, regulacion, literatura o anotacion curada | Alto indica que el nodo afecta multiples procesos biologicos relevantes. |
| `conservation_score` | numerico | 0-1 | score | Fase 2 desde conservacion de cepas o futura curacion Fase 3 | Alto indica conservacion amplia en cepas o linajes relevantes. |
| `functional_node_theory_score` | numerico | 0-1 o faltante controlado | score conceptual | futura combinacion Fase 3 | Alto indicaria un nodo funcional fuerte considerando contexto y robustez evolutiva. |

### Campos evolutivos

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `mutational_tolerance_score` | numerico | 0-1 o faltante controlado | penalizacion biologica potencial | mutagenesis, variacion natural, conservacion de dominios | Alto indica que el nodo tolera cambios y podria escapar mas facilmente. |
| `redundancy_penalty` | numerico | 0-1 | penalizacion | Fase 2 desde red funcional o futura evidencia de redundancia | Alto penaliza nodos con alternativas funcionales o rutas equivalentes. |
| `fitness_cost_score` | numerico | 0-1 o faltante controlado | score favorable | ensayos de fitness, literatura, modelos de costo | Alto indica que escapar del nodo tendria alto costo para el patogeno. |
| `compensation_difficulty_score` | numerico | 0-1 o faltante controlado | score favorable | evidencia de bypass, paralogia, red o metabolismo | Alto indica que compensar la perdida del nodo seria dificil. |
| `collateral_sensitivity_score` | numerico | 0-1 o faltante controlado | score favorable | evidencia de sensibilidad colateral o combinaciones | Alto indica que el escape podria crear vulnerabilidad a otro tratamiento. |
| `biofilm_escape_penalty` | numerico | 0-1 | penalizacion | evidencia de biofilm, tolerancia o persistencia | Alto indica riesgo de escape o tolerancia asociada a biofilm. |
| `horizontal_transfer_penalty` | numerico | 0-1 | penalizacion | plasmidos, islas, transferencia horizontal o literatura | Alto indica que transferencia horizontal podria facilitar escape. |
| `evolutionary_escape_risk_score` | numerico | 0-1 o faltante controlado | penalizacion agregada | futura auditoria evolutiva | Alto indica mayor riesgo de resistencia evolutivamente viable. |
| `evolutionary_space_constraint_score` | numerico | 0-1 o faltante controlado | score favorable | futura auditoria evolutiva | Alto indica que intervenir el nodo restringiria rutas viables de escape. |

### Subcapa `evolutionary_escape_risk`

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `mutation_tolerance_score` | numerico | 0-1 | riesgo | evidencia curada, mutagenesis, variacion natural o proxy derivada | Alto indica mayor tolerancia a mutaciones. |
| `functional_redundancy_escape_score` | numerico | 0-1 | riesgo | paralogia, redundancia de ruta, red funcional o curacion | Alto indica mayor capacidad de compensar el bloqueo. |
| `compensatory_pathway_score` | numerico | 0-1 | riesgo | rutas alternativas, bypass metabolico/regulatorio o curacion | Alto indica mayor capacidad compensatoria. |
| `fitness_cost_of_escape` | numerico | 0-1 | proteccion evolutiva | ensayos de fitness, esencialidad, conservacion o curacion | Alto reduce el riesgo porque escapar seria costoso. |
| `evolutionary_constraint_score` | numerico | 0-1 | proteccion evolutiva | conservacion, esencialidad, baja redundancia, red funcional | Alto reduce el riesgo por restriccion evolutiva. |
| `resistance_emergence_risk` | numerico | 0-1 | riesgo agregado | evidencia curada o derivacion transparente | Alto indica mayor probabilidad estimada de resistencia. |
| `multi_node_dependency_score` | numerico | 0-1 | proteccion evolutiva | red funcional, modulo, dependencia multiple | Alto reduce el espacio de escape viable. |
| `evolutionary_escape_risk_score` | numerico | 0-1 | penalizacion moderada | calculo configurado | Alto indica mayor riesgo global de escape. |
| `evolutionary_robustness_score` | numerico | 0-1 | score auxiliar | derivado | `1 - evolutionary_escape_risk_score`. |
| `reduced_evolutionary_space_score` | numerico | 0-1 | score auxiliar | derivado | Alto indica menor espacio evolutivo disponible. |
| `evolutionary_escape_risk_confidence` | texto | low/moderate/high | confianza cientifica | calculo segun evidencia disponible | Baja cuando no hay variables explicitas suficientes. |
| `evolutionary_escape_risk_status` | texto | categoria | auditoria | calculo | Distingue evidencia suficiente, derivada o insuficiente. |
| `evolutionary_escape_penalty_applied` | numerico | 0-1 | efecto en ranking | calculo configurado | Penalizacion aplicada sobre el score ajustado. |

### Campos de evidencia

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `evidence_quality_score` | numerico | 0-1 | score de confianza | literatura curada, experimento, base externa o proxy marcado | Alto indica evidencia mas confiable para la lectura Fase 3. |
| `confidence_ceiling` | numerico | 0-1 | limite de confianza | regla metodologica por fuente | Limita la confianza maxima si la evidencia es proxy, controlada o incompleta. |
| `evidence_source_type` | texto | categoria | categoria de procedencia | `experimental`, `curated_literature`, `external_database`, `controlled_provider`, `proxy`, `not_assessed` | Describe el tipo de evidencia. |
| `evidence_notes` | texto | libre | auditoria | curacion manual o reporte externo | Explica la evidencia o sus limitaciones. |
| `user_data_support` | booleano | verdadero/falso | soporte | `data_user/` o banderas `*_is_user_supplied` | Indica que existe evidencia aportada por el usuario. |
| `curated_literature_support` | booleano | verdadero/falso | soporte | literatura curada, DOI, PubMed o catalogo manual | Indica soporte bibliografico curado. |
| `external_database_support` | booleano | verdadero/falso | soporte | UniProt, STRING, VFDB, DEG, BV-BRC, InterPro u otra base estable | Indica evidencia de base externa trazable. |
| `experimental_support` | booleano | verdadero/falso | soporte fuerte | validacion experimental, knockout, Tn-seq o ensayo directo | Permite techo de confianza alto si esta presente. |
| `demo_data_penalty` | numerico | 0-1 | penalizacion | datos demo o `data_realism_flag=demo_only` | Penaliza evidencia que sirve para ejecutar el pipeline pero no para inferencia fuerte. |
| `controlled_provider_cap` | numerico | 0-1 | limite | proveedor controlado sin apoyo externo/curado/experimental | Marca el techo aplicable cuando solo hay contexto controlado. |

La capa `src/nodos_funcionales/evidence_quality.py` calcula estos campos sin reemplazar la logica previa de confianza. Sus techos metodologicos son:

- demo only: maximo 0.40;
- proveedor controlado solamente: maximo 0.50;
- base externa: maximo 0.70;
- literatura curada: maximo 0.80;
- datos del usuario + externa + curada: maximo 0.95;
- validacion experimental: maximo 1.00.

Si el score bruto supera el techo, se agrega `confidence_capped` en `audit_flags`.

### Campos terapeuticos

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `therapeutic_role_v3` | texto | categoria | categoria | futura clasificacion Fase 3 | Rol terapeutico considerando robustez evolutiva. |
| `recommended_combination_class` | texto | categoria | recomendacion conceptual | evidencia de sensibilidad colateral o curacion | Clase de combinacion sugerida, por ejemplo nodo de biofilm + beta-lactamico. |
| `combination_rationale` | texto | libre | auditoria | curacion manual o literatura | Razon biologica de la combinacion propuesta. |

### Campos de auditoria

| Campo | Tipo | Rango | Clase | Fuente esperada | Interpretacion |
| --- | --- | --- | --- | --- | --- |
| `audit_flags` | texto | lista separada por `;` | auditoria | validacion o curacion | Marca faltantes, proxies, evidencia debil o conflictos. |
| `phase3_notes` | texto | libre | auditoria | curacion manual | Comentario interpretativo sobre la evaluacion Fase 3. |

## Reglas de compatibilidad Fase 3

- Si los CSV Fase 3 no existen, Fase 1/Fase 2 siguen ejecutandose.
- Las penalizaciones faltantes se inicializan de forma segura y no rompen el pipeline.
- Los scores conceptuales faltantes pueden quedar como faltante controlado.
- `phase3.enabled` esta en `false`; por tanto no cambia rankings.
- Cualquier futura activacion debe mantener procedencia, confianza, flags de proxy y descomposicion de variables.
