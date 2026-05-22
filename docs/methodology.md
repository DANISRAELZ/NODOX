# Metodología

Nodos Funcionales es una plataforma bioinformatica multiorganismo para la
priorizacion explicable de blancos terapeuticos bacterianos. Cualquier organismo
bacteriano puede analizarse mediante un workspace independiente, capas
estandarizadas y auditoria de procedencia. Los organismos nombrados en demos,
tests o cache son ejemplos de uso y validacion, no dependencias del modelo.

## Cierre metodologico theory-first

La Teoria de Nodos Funcionales es el centro conceptual del proyecto. El
software, los pipelines, los importadores, los reportes, los snapshots
controlados y las validaciones online solo operacionalizan y auditan esa teoria:
no la sustituyen ni convierten un organismo ejemplo en organismo central.

La arquitectura final se interpreta como una cadena de auditoria:

1. Teoria de Nodos Funcionales: define que un blanco terapeutico debe evaluarse
   por su posicion funcional, contexto biologico, trazabilidad y capacidad de
   restringir rutas de escape.
2. Capas de evidencia: integran datos del usuario, evidencia externa trazable,
   referencias controladas, cache, proxy, demo o faltantes, siempre con
   procedencia explicita.
3. Subcapa evolutiva: conserva como eje vital `evolutionary_escape_risk`,
   `evolutionary_constraint`, `mutation_tolerance`, `pathway_redundancy`,
   `paralog_count`, `mobile_context`, `hgt_context`, `recombination_context` y
   `resistance_association`.
4. Snapshots controlados: validan contratos de estructura y procedencia en
   ejemplos separados como PAO1, Corynebacterium y H37Rv, sin sustituir datos
   reales del usuario ni evidencia externa fresca.
5. Validacion `user_curated`: usa datos reales aportados o revisados por el
   usuario en un workspace separado, sin mezclar demo, proxy, cache,
   `controlled_reference` u online fresco como evidencia principal. Cada dataset
   real debe acompanarse de un manifest trazable basado en
   `data_templates/user_curated_dataset_manifest_template.csv`.
   La especificacion futura de scoring controlado `user_curated` se documenta
   en `docs/user_curated_controlled_scoring_spec.md` sin implementarse todavia.
6. Limites interpretativos: ausencia o insuficiencia de evidencia no equivale a
   bajo riesgo, ausencia biologica, evidencia negativa ni irrelevancia
   terapeutica.
7. Validacion online futura: STRING y UniProt deben ejecutarse solo bajo modos
   `online_optional` o protocolos auditables, en workspaces separados y sin
   mezclar resultados frescos con snapshots, cache mutable, proxy, demo o datos
   de usuario.

El enfoque sigue siendo multiorganismo: cualquier usuario debe poder ingresar
informacion de cualquier organismo bacteriano, siempre que las capas se declaren
con procedencia, confianza y limitaciones suficientes.

## Objetivo

La Fase 2 transforma un ranking lineal en una plataforma modular y auditable de
priorizacion terapeutica basada en evidencia. La plataforma no es un predictor
clinico definitivo.

## Principios

- interpretabilidad por encima de complejidad innecesaria
- trazabilidad de cada variable derivada
- separación entre evidencia positiva, negativa y desconocida
- placeholders explícitos cuando aún no existe una medición biológica real
- comparación obligatoria con el baseline legacy

## Flujo

1. Validar tablas crudas.
2. Normalizar identificadores y metadatos canónicos.
3. Integrar evidencia en una tabla maestra.
4. Derivar features continuas e indicadores de confianza.
5. Calcular scores por estrategia.
6. Integrar `meta_priority_score`.
7. Estimar riesgo de escape evolutivo y su penalizacion moderada auditable.
8. Analizar sensibilidad con escenarios alternativos.
8. Exportar ranking, comparación y reporte.

La prioridad terapeutica y la confianza de evidencia se mantienen separadas.
`therapeutic_priority_score` expresa una lectura relativa de prioridad dentro de
las reglas actuales, mientras `evidence_confidence_score` expresa cuanto soporte
trazable existe para interpretar esa lectura. Por eso un score alto no se
promueve automaticamente a confianza alta.

## Tratamiento del faltante

La Fase 2 evita interpretar automáticamente “desconocido” como “negativo”.

- Las columnas crudas pueden permanecer faltantes.
- Los scores usan defaults neutros explícitos cuando hace falta un valor numérico.
- Los faltantes y placeholders quedan señalados en `missing_evidence_flags`.

## Placeholders actuales

Se dejan preparados con defaults explícitos cuando no hay tabla opcional:

- red funcional
- conservación entre cepas
- parte de la seguridad del hospedero avanzada que requeriría dominios o anotación funcional humana

Estos placeholders no deben leerse como una medición biológica definitiva.

Cuando existen tablas opcionales en `data_raw/`, la Fase 2 ya reemplaza esos defaults por
valores observados para:

- conservación entre cepas o aislados
- red funcional
- anotación de solapamiento de dominios y criticidad del hospedero

## Proxies disponibles con datos actuales

Para endurecer Fase 2 sin inventar datos externos, el pipeline ya usa proxies explícitas
basadas en evidencia observada:

- acceso al sitio de infección a partir de localización
- reducción potencial de daño al hospedero a partir de virulencia y accesibilidad
- asociación con severidad a partir de fuerza de virulencia
- impacto clínico como proxy combinada

Cada una queda marcada como `*_is_proxy` en la tabla de features.

## Estado metodológico actual

- La madurez de cada score depende de la evidencia disponible en el workspace
  del organismo analizado, no de un organismo demo.
- `antibiotic_target_score` suele ser la capa más madura cuando hay señal
  observada de esencialidad, seguridad para el hospedero, conservación y
  factibilidad.
- `antivirulence_target_score` es interpretable y útil para comparar estrategias, pero sigue
  dependiendo de proxies para impacto clínico y reducción de daño.
- `functional_node_score` ya acepta datos reales de red, aunque su significado biológico sigue
  dependiendo mucho de cómo se construya esa red aguas arriba.
## Riesgo de escape evolutivo

El modelo incluye la subcapa opcional `evolutionary_escape_risk`. Esta subcapa
pregunta si un candidato podria ser evadido por mutaciones toleradas, redundancia
funcional, rutas compensatorias o bajo costo adaptativo.

Cuando hay datos curados, el pipeline usa los campos explicitos del CSV
`evolutionary_escape_risk.csv`. Si faltan, puede derivar una lectura conservadora
desde capas ya resueltas como conservacion, esencialidad, red funcional y
redundancia. Esa derivacion queda marcada con baja confianza cuando no hay
variables explicitas suficientes.

El ranking principal conserva `meta_priority_score` por compatibilidad y agrega
`evolutionary_adjusted_meta_priority_score` para mostrar el efecto de la
penalizacion evolutiva configurable.

## Lectura conservadora

La interpretacion conservadora advierte sobre evidencia proxy, confianza baja,
redundancia alta, `paralog_count` alto, `mobile_context`, `hgt_context`,
`recombination_context` y `resistance_association`. Esa lectura evita tratar
faltantes o proxies como bajo riesgo.

La subcapa evolutiva modula robustez y escape, pero no reemplaza los ejes de
funcionalidad, selectividad, accesibilidad y evidencia que sostienen la Teoria
de Nodos Funcionales.
