# Auditoria de madurez multi-organismo

## 1. Estado del baseline

- `git status --short`: limpio al inicio de la auditoria. No habia cambios inesperados antes de escribir este reporte.
- Pruebas offline: el estado recibido de cierre theory-first indica `pytest -p no:cacheprovider -m "not online" -q` al 100% sin fallos. En esta sesion, `pytest` no estaba disponible en PATH. Al repetir con el Python empaquetado de Codex, la suite avanzo hasta `31%` y el proceso termino con codigo `1` sin mostrar resumen de fallos en la salida capturada. No quedaron cambios en git despues de ese intento.
- Corrida PAO1: el estado recibido indica corrida correcta de `run_pipeline.py` para `Pseudomonas aeruginosa` PAO1, con `validation_rows=105`, `integrated_rows=11`, `feature_rows=11`, `score_rows=11` y `ranking_nodos.csv` generado en `data_sessions/pseudomonas_aeruginosa_pao1/results/`.
- Estado del cache: no se modifico cache operativo durante esta auditoria. El `acquisition_manifest.json` de PAO1 reporta resolucion taxonomica desde cache local, proveedor `api_stub`, `cache_hit=true`, `api_success=false` y `fallback_reason=stub_mode_requested`.

## 2. Alcance de la auditoria

Archivos y rutas revisadas:

- `run_pipeline.py`
- `src/nodos_funcionales/`
- `config/`
- `data_templates/`
- `docs/`
- `tests/`
- `scripts/`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/`

Modulos revisados con mas detalle:

- `src/nodos_funcionales/reporting.py`
- `src/nodos_funcionales/scoring.py`
- `src/nodos_funcionales/integration.py`
- `src/nodos_funcionales/layer_resolver.py`
- `src/nodos_funcionales/layer_registry.py`
- `src/nodos_funcionales/discovery.py`
- `src/nodos_funcionales/evidence_quality.py`
- `src/nodos_funcionales/user_explanations.py`

Outputs revisados:

- `data_sessions/pseudomonas_aeruginosa_pao1/results/ranking_nodos.csv`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/discovery_report.md`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/acquisition_manifest.json`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/report_phase2.md`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/top10_scientific_audit.md`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/data_provenance_summary.csv`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/layer_resolution_summary.csv`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/layer_resolution_summary.md`
- `data_sessions/pseudomonas_aeruginosa_pao1/results/provenance_user_summary.md`

## 3. Acoplamiento a organismos especificos

| archivo | referencia encontrada | tipo de acoplamiento | clasificacion A/B/C/D | recomendacion |
| --- | --- | --- | --- | --- |
| `config/demo_organisms.json` | `Pseudomonas aeruginosa`, `PAO1` | Catalogo explicito del demo empaquetado | A | Mantener. Es correcto mientras siga marcado como `packaged_demo` y no se use como evidencia biologica real. |
| `config/taxon_aliases.json` | PAO1, Corynebacterium, H37Rv | Alias locales de resolucion taxonomica | B | Mantener por ahora, pero documentar que son semillas de resolucion, no lista cerrada de organismos soportados. |
| `config/taxon_resolution_cache.json` | PAO1, Corynebacterium, H37Rv, Example bacterium | Cache reproducible de taxonomia | A/B | Mantener como cache auditable. Revisar que las entradas stub o ejemplo no se presenten como resolucion online real. |
| `run_pipeline.py` | `demo` en CLI y advertencias | Control de uso de datos demo | A | Mantener. La advertencia `[WARN] Demo data used; confidence capped` es saludable para el usuario. |
| `src/nodos_funcionales/discovery.py` | `demo`, `template`, `packaged_demo` | Preparacion de workspaces y plantillas | A | Mantener. La logica esta acotada por `allow_demo_data` y manifiesto. |
| `src/nodos_funcionales/layer_resolver.py` | `external+demo_raw`, `demo_raw` | Resolucion por capa con relleno demo bajo estrategia | B | Mantener, pero revisar la nomenclatura para que el usuario vea claramente cuando un merge usa demo como gap fill. |
| `data_templates/evolutionary_escape_risk_template.csv` | `Pseudomonas aeruginosa`, `PAO1`, `example_candidate` | Ejemplo dentro de plantilla generica | B | Cambiar en un commit menor a un organismo ficticio o a placeholders (`ORGANISM_TO_REPLACE`, `STRAIN_TO_REPLACE`) para evitar lectura como plantilla PAO1. |
| `data_templates/organism_profile_template.csv` | `Pseudomonas aeruginosa`, `PAO1` | Ejemplo dentro de plantilla de perfil | B | Reemplazar por placeholders o por `Example bacterium` claramente ficticio. |
| `scripts/run_demo.ps1` | PAO1 | Script de demo principal | A | Mantener como demo historico controlado. |
| `scripts/run_cpseudo_dryrun.ps1` | Corynebacterium pseudotuberculosis | Script de dry-run especifico | B | Renombrar o complementar con un script generico parametrizable; conservar el caso como ejemplo si queda documentado. |
| `scripts/run_corynebacterium_online_demo.ps1` | Corynebacterium pseudotuberculosis | Demo online organism-first | A/B | Aceptable porque declara que es ejemplo; a medio plazo conviene tener `run_online_demo.ps1` parametrico. |
| `tests/test_*api.py` | PAO1 y Corynebacterium | Fixtures y mocks de proveedores externos | A | Aceptable. Cubren cache, API, fallback y modos offline/online. |
| `tests/test_curated_snapshots.py` | PAO1, Corynebacterium, H37Rv | Casos de snapshot y validacion cruzada | A | Mantener. Solo asegurar que `controlled_fixture` y demo no se mezclen con evidencia real. |
| `tests/test_generic_annotation_import.py` | Corynebacterium biovar ovis | Fixture de importacion generica con organismo concreto | B | Aceptable como prueba, pero podria parametrizarse o renombrarse el caso para que no parezca dominio principal. |
| `tests/test_multiorganism_orientation.py` | Example bacterium, PAO1 | Pruebas de orientacion multi-organismo | A | Mantener. Es una buena defensa contra acoplamiento conceptual. |
| `docs/project_scope.md`, `docs/project_boundaries.md`, `docs/multiorganism_architecture.md` | PAO1, Corynebacterium, H37Rv | Documentacion de alcance | A | Mantener. Estos documentos aclaran que son ejemplos, no limites biologicos. |
| `docs/ranking_snapshots.md` | PAO1, Corynebacterium, H37Rv | Politica de snapshots | A/B | Mantener, pero seguir separando snapshot demo, snapshot real congelado y evidencia externa real. |
| `docs/online_validation_protocol.md` y `docs/online_validation_runs/*` | PAO1 | Registros de validacion online | A | Mantener como bitacora historica. No es acoplamiento operativo. |
| `data_sessions/pseudomonas_aeruginosa_pao1/results/*` | PAO1 | Output generado de corrida demo/control | A | No versionar sesiones completas nuevas. Usar solo como evidencia de auditoria local. |

Resumen de clasificacion:

- A) Fixture/demo aceptable: mayoria de scripts, tests, docs historicos y outputs PAO1.
- B) Deuda tecnica menor: plantillas con valores PAO1, scripts de organismo concreto que podrian parametrizarse, nomenclatura de merges con demo.
- C) Riesgo real: inconsistencia de procedencia entre manifest/discovery y algunos reportes de usuario, detallada abajo.
- D) Bloqueo critico: no se encontro bloqueo critico para ejecutar o auditar enfoque multi-organismo.

## 4. Exposicion de la Teoria de Nodos en outputs

| variable o componente | aparece en codigo | aparece en ranking | aparece en reporte | interpretacion para usuario | pendiente |
| --- | --- | --- | --- | --- | --- |
| `functional_node_score` | si | si | si | Score funcional/red usado en priorizacion. | Mantener interpretacion clara como hipotesis, no validacion. |
| `antibiotic_target_score` | si | si | si | Senal de blanco antibiotico clasico. | Mantener descomposicion de drivers. |
| `antivirulence_target_score` | si | si | si | Senal de estrategia antivirulencia. | Mantener advertencias de evidencia proxy/demo. |
| `meta_priority_score` | si | si | si | Score integrado de prioridad. | Explicar mejor diferencia entre v2/legacy y v3 cuando ambos existan. |
| `therapeutic_role` | si | si | si | Rol terapeutico interpretable (`bactericidal_candidate`, `antivirulence_candidate`, etc.). | Mantener reglas visibles y estabilidad con/sin proveedor controlado. |
| `therapeutic_priority_components` | si, como texto en `candidate_audit_summary` | no como columna literal | si, embebido en resumen | Descomposicion de la prioridad terapeutica. | Agregar alias/columna directa o documentar que la columna actual es `therapeutic_priority_contribution_summary`. |
| `theory_context` | si | no | no | Contexto conceptual de teoria. | Exponer en reportes de usuario o mapearlo a `functional_node_theory_*`. |
| `provenance_context` | si | no | no | Contexto de procedencia resumido. | Exponer como seccion compacta por candidato. |
| `evolutionary_escape_risk` | si | si | si | Riesgo de escape evolutivo; en PAO1 aparece como desconocido o derivado con baja confianza. | Mantener advertencia de que desconocido no significa bajo riesgo. |
| `evolutionary_constraint` | si | si | si | Restriccion evolutiva usada en penalizacion/robustez. | Mejorar interpretacion no tecnica. |
| `mutation_tolerance` | si | si | si | Tolerancia mutacional observada o derivada. | Separar con mas fuerza observado vs derivado. |
| `pathway_redundancy` | si | si | si | Redundancia de ruta o compensacion posible. | Conectar mejor con datos reales de rutas para nuevos organismos. |
| `paralog_count` | si | si | si | Senal de redundancia por paralogos. | Mantener como incompleto si no hay anotacion real. |
| `mobile_context` | si | si | si | Contexto movil asociado al nodo. | Agregar fuentes reales incrementales antes de usarlo como senal fuerte. |
| `hgt_context` | si | si | si | Transferencia horizontal asociada. | Igual que `mobile_context`: distinguir ausencia de evidencia de evidencia negativa. |
| `recombination_context` | si | si | si | Contexto de recombinacion. | Requiere evidencia organism-specific para madurez alta. |
| `resistance_association` | si | si | si | Asociacion con resistencia. | Separar asociacion curada de inferencia o faltante. |

Lectura general:

- El ranking principal de PAO1 expone una cantidad amplia de columnas teoricas, terapeuticas, evolutivas y de procedencia.
- `report_phase2.md` y `top10_scientific_audit.md` explican bien los limites: score alto no es validacion experimental, ausencia de evidencia no es evidencia negativa y demo/proxy/cache no son evidencia externa real.
- La capa theory-first v3 existe en codigo y reportes, pero en la corrida PAO1 revisada aparece en varios campos como `not_assessed`, `nan` o `0.0000`. Esto no bloquea la ejecucion, pero si es un pendiente de madurez interpretativa para la siguiente fase.

## 5. Separacion de evidencia y procedencia

El sistema distingue la procedencia en varios niveles:

- `user_data`: aparece en el resolvedor por capa con `<layer>_is_user_supplied` y en reportes como capas de usuario. La lectura del usuario final todavia puede mejorar porque algunas capas `raw` terminan descritas como `user_curated` en `provenance_user_summary.md`.
- `curated`: aparece como `curated`, `curated_snapshot`, `curated_literature_or_catalog` y en `literature_support`. Es visible en ranking y reportes.
- `cache`: aparece como `cache_hit`, `cache_first_or_cache_hit`, `<layer>_is_cached` y `retrieval_status`. Se conserva en `layer_resolution_summary.csv`.
- `demo`: aparece en `discovery_report.md`, `acquisition_manifest.json`, `data_provenance_summary.csv`, `data_realism_flag`, `demo_data_penalty`, `template_or_demo_records.csv` y advertencias de CLI.
- `proxy`: aparece en scores y resumenes como `proxy_host_damage_score`, `proxy_infection_site_access_score`, `proxy_infection_context_score`, `is_proxy` y `proxy_inference`.
- `online_real`: aparece en arquitectura y proveedores reales, especialmente UniProt para `localization` y STRING para `functional_network`; tambien se registra mediante source/retrieval/confidence en el resolvedor.
- `missing_evidence`: aparece como `missing`, `template_or_empty`, `missing_input`, `unknown_missing_evidence`, `missing_evidence_flags` y colas de curacion.
- `negative_evidence`: esta separada conceptualmente de faltante/demo/proxy. En codigo y docs se insiste en que ausencia de evidencia no equivale a evidencia negativa; la fase 3 cuenta `negative_evidence_layer_count` solo cuando hay senales trazables.

Hallazgo principal:

La separacion existe y es mucho mejor que una simple tabla de scores, pero hay una inconsistencia a corregir. El `acquisition_manifest.json` y `discovery_report.md` dicen que varias capas PAO1 fueron `packaged_demo`, mientras que `layer_resolution_summary.csv` las resume como `raw` y `provenance_user_summary.md` puede mostrarlas como `user_curated`. Esto es un riesgo real de comunicacion: el usuario podria interpretar datos demo copiados a `data_raw/` como evidencia curada propia.

## 6. Riesgos para generalizacion multi-organismo

Criticos:

- No se encontraron bloqueos criticos de arquitectura. El pipeline acepta `organism`, `strain` opcional, plantillas y modos offline/cache/online opcional.

Medios:

- La procedencia puede degradarse al pasar de manifest/discovery a resumen de usuario: `packaged_demo` puede aparecer como `raw` o `user_curated`.
- Algunas plantillas contienen PAO1 como ejemplo concreto. Esto no rompe ejecucion, pero puede orientar mal a usuarios que preparan organismos nuevos.
- `functional_node_theory_score` y `therapeutic_role_v3` existen, pero en la corrida PAO1 revisada aparecen como no evaluados. La teoria esta implementada, pero su exposicion operativa aun no esta madura para todos los outputs.
- Las capas de contexto terapeutico (`clinical_impact`, `curated_disease_context`, `therapy_site_context`) dependen todavia de plantillas, proxies o curacion pendiente en la corrida PAO1.
- La resolucion taxonomica del demo PAO1 usa cache/stub en esta ejecucion; esto es reproducible, pero no demuestra madurez online para organismos nuevos.

Bajos:

- Referencias a PAO1, Corynebacterium y H37Rv en docs y tests son mayormente aceptables y bien explicadas.
- Scripts especificos de demo son utiles para regresion, aunque conviene agregar equivalentes parametrizables.
- Los outputs PAO1 son extensos y utiles para auditoria, pero no deberian multiplicarse como `data_sessions` versionados.

## 7. Recomendaciones priorizadas

Prioridad inmediata:

- Corregir la narrativa de procedencia para que datos `packaged_demo` copiados a `data_raw/` no aparezcan ante el usuario como `user_curated`.
- Documentar o exponer una columna directa para `therapeutic_priority_components`, usando la columna ya existente `therapeutic_priority_contribution_summary` como base.
- Agregar una nota en reportes cuando `functional_node_theory_score` o `therapeutic_role_v3` esten `not_assessed`, explicando que la teoria esta presente pero esa corrida no tiene evidencia suficiente para evaluar v3.

Prioridad media:

- Reemplazar ejemplos PAO1 en `data_templates/evolutionary_escape_risk_template.csv` y `data_templates/organism_profile_template.csv` por placeholders o un ejemplo ficticio claro.
- Crear o ajustar tests que ejecuten un organismo generico minimo sin demo, con datos incompletos, y validen que el pipeline falla o continua con mensajes correctos segun corresponda.
- Parametrizar los scripts de dry-run online para evitar que Corynebacterium parezca caso privilegiado.
- Agregar pruebas de consistencia entre `acquisition_manifest.json`, `layer_resolution_summary.csv`, `provenance_user_summary.md` y `ranking_nodos.csv`.

Prioridad baja:

- Consolidar docs historicos para reducir repeticion de PAO1 sin perder trazabilidad.
- Preparar validaciones cruzadas documentadas con H37Rv y otro organismo con datos curados minimos.
- Mejorar textos no tecnicos de variables evolutivas (`hgt_context`, `mobile_context`, `recombination_context`) en reportes.

## 8. Proximos commits sugeridos

1. Documentacion de auditoria
   - Agregar `docs/multiorganism_maturity_audit.md`.
   - No tocar scoring ni snapshots.

2. Ajustes menores de reportes
   - Alinear `provenance_user_summary.md` y `layer_resolution_summary.*` para preservar `packaged_demo`, `demo`, `controlled`, `cache`, `proxy`, `missing` y `external_real` sin reclasificaciones ambiguas.
   - Exponer `therapeutic_priority_components` como alias legible o documentar explicitamente `therapeutic_priority_contribution_summary`.

3. Tests multi-organismo
   - Agregar test de organismo generico con strain opcional.
   - Agregar test de datos minimos/incompletos sin demo.
   - Agregar test de consistencia de procedencia entre manifest, integration y reportes.

4. Limpieza de fixtures/demo
   - Cambiar ejemplos PAO1 en plantillas por placeholders.
   - Parametrizar scripts `run_cpseudo_dryrun.ps1` y `run_corynebacterium_online_demo.ps1` o agregar equivalentes genericos.

5. Validaciones con organismos adicionales
   - Preparar una corrida controlada para H37Rv con cache/snapshot trazable.
   - Preparar un organismo generico con datos de usuario minimos.
   - Mantener PAO1 como demo/regresion, no como prueba unica de madurez multi-organismo.
