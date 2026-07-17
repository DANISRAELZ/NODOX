# Auditoria de procedencia de capas

Esta auditoria describe de donde puede venir cada capa de evidencia del
pipeline "Nodos Funcionales". Es una auditoria descriptiva: no modifica pesos,
scores, rankings ni contratos publicos del pipeline.

## Etiquetas de procedencia

- `user_curated`: dato revisado o proporcionado manualmente por el usuario.
- `organism_specific`: evidencia especifica para el organismo o cepa analizada.
- `external_real`: conexion o fuente externa real, verificable y trazable.
- `external_general`: evidencia externa general, no necesariamente especifica para el organismo/cepa.
- `external_stub`: funcion o proveedor simulado, sin conexion real.
- `cache_hit`: dato resuelto desde cache en una ejecucion concreta.
- `cache_possible`: la capa puede usar cache si existe.
- `raw_local`: archivo local de entrada sin curacion explicita.
- `internally_computed`: valor calculado a partir de datos del propio proyecto.
- `controlled_provider`: dato generado desde reglas internas controladas, no desde una base viva.
- `proxy`: aproximacion indirecta, no evidencia directa.
- `demo`: dato de ejemplo.
- `template_only`: solo existe plantilla, sin datos reales.
- `literature_curated`: evidencia bibliografica manualmente curada.
- `disabled_by_default`: existe, pero no participa a menos que se active.
- `missing`: capa ausente.
- `pending_connection`: capa disenada o deseable, pero aun sin conexion real.

## Jerarquia metodologica de evidencia

1. Evidencia curada por el usuario, especifica del organismo y trazable.
2. Evidencia externa real, verificable y preferentemente cacheada.
3. Evidencia calculada internamente desde datos reales del usuario.
4. Evidencia local/raw.
5. Evidencia externa general no especifica.
6. Evidencia proxy o proveedor controlado.
7. Datos demo.

Valores normalizados usados en `evidence_priority_level`:

- `1_user_curated_organism_specific`
- `2_external_real_traceable`
- `3_internally_computed_from_user_data`
- `4_raw_local`
- `5_external_general`
- `6_proxy_or_controlled`
- `7_demo`
- `8_missing_or_template_only`

## Matriz de auditoria

| Capa | Estado actual | Etiquetas de procedencia | Procedencia principal | Procedencia secundaria | Nivel de prioridad de evidencia | Razon de prioridad | ¿Base externa real? | ¿Usa cache? | ¿Usa demo? | ¿Usa proxy/controlado? | ¿Requiere curacion manual? | ¿Participa en score? | Riesgo cientifico | Recomendacion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| essentiality | Parcialmente conectada | user_curated, organism_specific, external_real, cache_possible, raw_local, demo | `data_user/essentiality.csv` si existe; si no, cache/external/raw segun resolvedor | DEG `deg_real`; `data_raw`; `data_demo`; `data_templates` | `2_external_real_traceable` | Tiene proveedor DEG real y cacheable, pero la mejor evidencia es curacion especifica por usuario cuando exista. | Si | Si | Si | No | Si | Si | Medio | Usar esencialidad curada por organismo/cepa como fuente primaria; DEG como soporte trazable. |
| virulence | Parcialmente conectada | user_curated, organism_specific, external_real, cache_possible, raw_local, demo | `data_user/virulence.csv` si existe; si no, VFDB/cache/raw | VFDB `vfdb_real`; `data_raw`; `data_demo`; plantillas | `2_external_real_traceable` | Tiene proveedor VFDB real y cacheable; la virulencia debe leerse segun organismo, cepa y contexto de infeccion. | Si | Si | Si | No | Si | Si | Medio | Separar factores de virulencia confirmados de asociaciones generales o inferidas. |
| human_homologs | Conectada de forma conservadora | user_curated, external_real, external_general, external_stub, cache_possible, raw_local, demo | `data_user/human_homologs.csv` si existe | DIAMOND contra proteoma humano de referencia; UniProt por nombre queda como evidencia auxiliar no concluyente | `2_external_real_traceable` cuando hay TSV/alineamiento; `6_proxy_or_controlled` si queda no resuelto | Las coincidencias por nombre no elevan `human_homolog`; los no-hit se interpretan solo como sin similitud detectable bajo parametros usados. | Si | Si | Si | Si | Si | Si | Medio | Agregar busqueda reciproca y dominios conservados para separar ortologia fuerte de similitud parcial. |
| localization | Conectada a fuente externa real | user_curated, organism_specific, external_real, cache_possible, raw_local, demo | `data_user/localization.csv` si existe | UniProt REST `uniprot_real`; cache; raw/demo | `2_external_real_traceable` | UniProt REST esta implementado y cacheable; el usuario puede sobreescribir con evidencia curada. | Si | Si | Si | No | No | Si | Medio | Distinguir localizacion experimental, predicha o inferida; mantener cache para reproducibilidad. |
| strain_conservation | Parcialmente conectada | user_curated, organism_specific, external_real, cache_possible, raw_local, demo, proxy | `data_user/strain_conservation.csv` si existe | BV-BRC `bvbrc_real`; defaults para variantes si no hay datos | `2_external_real_traceable` | BV-BRC es real/cacheable para presencia por cepa; algunos campos pueden ser aproximados. | Si | Si | Si | Si | Si | Si | Medio | Documentar conjunto de cepas y separar presencia observada de conservacion/variantes inferidas. |
| functional_network | Conectada a fuente externa real | user_curated, organism_specific, external_real, cache_possible, raw_local, internally_computed, demo, proxy | STRING `string_real` por `external_preferred` | Cache, raw/demo, metricas derivadas de red | `2_external_real_traceable` | STRING es real/cacheable; centralidad y metricas asociadas son calculadas internamente desde la red. | Si | Si | Si | Si | No | Si | Medio | Reportar las metricas de red como derivadas, no como evidencia experimental directa. |
| clinical_impact | Demo/proxy | user_curated, cache_possible, raw_local, internally_computed, controlled_provider, proxy, demo | `controlled_therapeutic_context_v2` si no hay user/cache/raw | Proxy interno `scoring_proxy_default`; plantilla para curacion | `6_proxy_or_controlled` | Se genera por proveedor controlado o proxies; no es base clinica externa viva. | No | Si | No | Si | Si | Si | Alto | Reemplazar con curacion clinica o evidencia experimental antes de usar para conclusiones biologicas fuertes. |
| curated_disease_context | Demo/proxy | user_curated, cache_possible, raw_local, internally_computed, controlled_provider, proxy, demo | `controlled_therapeutic_context_v2` si no hay user/cache/raw | Proxy de contexto de infeccion derivado en scoring | `6_proxy_or_controlled` | La relevancia en infeccion se estima con reglas controladas si no hay evidencia curada. | No | Si | No | Si | Si | Si | Alto | Conectar datos de expresion/relevancia in vivo o curacion manual especifica del organismo. |
| therapy_site_context | Demo/proxy | user_curated, cache_possible, raw_local, internally_computed, controlled_provider, proxy, demo | `controlled_therapeutic_context_v2` si no hay user/cache/raw | Proxy de accesibilidad derivado de localizacion | `6_proxy_or_controlled` | La accesibilidad terapeutica es inferida; no prueba alcanzabilidad farmacologica real. | No | Si | No | Si | Si | Si | Alto | Curar datos de sitio de infeccion, permeabilidad o evidencia farmacologica antes de decisiones fuertes. |
| host_annotation | InterPro con essentialidad humana auxiliar | user_curated, raw_local, cache_possible, external_real, controlled_provider, demo, template_only | `data_user/host_annotation.csv`, `data_cache/host_annotation.csv`, `data_external/host_annotation.csv` o `data_raw/host_annotation.csv` | Proveedor `interpro_domain_overlap`; essentialidad humana auxiliar; fallback `controlled_host_annotation_v1` desde `human_homologs` resuelto | `2_external_real_traceable` | InterPro aporta dominios reales y la essentialidad humana puede modular criticidad; si faltan dominios comparables, cae a fallback controlado y lo marca. | Si | Si | Si | Si | Si | Si | Medio | Agregar expresion por tejido o contexto celular hospedero para interpretar seguridad como fuerte. |
| literature_support | Desactivada por defecto | literature_curated, disabled_by_default, template_only, demo, user_curated | Curacion bibliografica manual del usuario | Demo con `pending_manual_curation`; reportes interpretativos | `8_missing_or_template_only` | Existe como estructura de curacion/reporting, pero no participa en scoring y el demo no contiene referencias verificadas. | No | Si | Si | No | Si | No | Medio | Mantener fuera del score hasta tener DOI/URL y curacion manual verificable por candidato. |

## Observaciones clave

- El resolvedor ya prioriza `data_user/` sobre cache, proveedores externos y
  `data_raw/` para estrategias `user_preferred`.
- `functional_network` usa `external_preferred`, por lo que STRING puede
  materializarse antes que datos locales si no se reconfigura.
- `clinical_impact`, `curated_disease_context` y `therapy_site_context` no son
  bases externas reales: son proveedores controlados y proxies documentados.
- `literature_support` es interpretativa y esta desactivada para scoring.
- `cache_hit` solo puede afirmarse para una ejecucion concreta desde el
  manifest; en esta auditoria estatica se marca `cache_possible`.

## Archivo machine-readable

La version estructurada de esta matriz esta en:

- `docs/layer_source_audit.json`

Ese archivo debe usarse para validaciones automaticas o para generar resumenes
de procedencia sin tocar los resultados cientificos.
## Auditoria por variable en Fase 3

Fase 3 genera:

- `results/layer_evidence_audit.csv`
- `results/layer_evidence_summary.csv`

Cada fila de `layer_evidence_audit.csv` describe una variable de entrada:

- `layer_name`
- `variable_name`
- `value`
- `evidence_source_type`
- `evidence_quality`
- `evidence_is_missing`
- `evidence_is_demo`
- `evidence_is_proxy`
- `evidence_is_negative`
- `source_file_or_provider`
- `explanation`

Ponderacion inicial:

- `user_curated`: 1.00
- `literature_curated`: 0.95
- `external_real`: 0.90
- `computed_from_real_data`: 0.80
- `controlled_provider`: 0.60
- `proxy_inference`: 0.40
- `default_value`: 0.20
- `demo_data`: 0.10
- `missing`: 0.00

Estas ponderaciones son configurables en
`phase3.evidence_quality.source_type_weights`.

## Reduccion de demo en PAO1

Para PAO1, algunas capas pueden resolverse ahora desde catalogos curados
offline derivados de fuentes online estables:

- `essentiality`: `data_external/curated_catalogs/essentiality/pseudomonas_aeruginosa_pao1.csv`
- `virulence`: `data_external/curated_catalogs/virulence/pseudomonas_aeruginosa_pao1.csv`
- `localization`: `data_external/curated_catalogs/localization/pseudomonas_aeruginosa_pao1.csv`
- `literature_support`: `data_external/curated_catalogs/literature_support/pseudomonas_aeruginosa_pao1.csv`

Estas filas pasan por `layer_resolver.py` usando `curated_online_examples`.
Cuando una fila curada coincide con un candidato, reemplaza al demo para esa
variable. Cuando no hay fila curada, el demo puede seguir usandose para mantener
compatibilidad de la corrida, pero queda marcado como `demo_data` y no aumenta
la confianza cientifica.
