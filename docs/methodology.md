# Metodología

Nodos Funcionales es una plataforma bioinformatica multiorganismo para la
priorizacion explicable de blancos terapeuticos bacterianos. Cualquier organismo
bacteriano puede analizarse mediante un workspace independiente, capas
estandarizadas y auditoria de procedencia. Los organismos nombrados en demos,
tests o cache son ejemplos de uso y validacion, no dependencias del modelo.

## Objetivo

La Fase 2 transforma un ranking lineal en una plataforma modular y auditable.

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
