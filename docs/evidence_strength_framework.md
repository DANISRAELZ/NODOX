# Marco de fuerza de evidencia

Este marco separa el valor numerico del ranking de la calidad metodologica de
la evidencia. Un candidato puede tener score alto y, aun asi, evidencia debil si
depende de demo, proxy, proveedor controlado o capas incompletas.

## Categorias

### `strong`

Evidencia fuerte significa que el candidato tiene:

- evidencia especifica del organismo o cepa,
- fuente curada por usuario o externa real trazable,
- buena cobertura de capas,
- dependencia baja o nula de demo/proxy,
- procedencia clara en manifest o reportes.

### `moderate`

Evidencia moderada significa que hay una mezcla util de datos reales e
indirectos, con cobertura razonable, pero aun existen capas faltantes,
procedencia mixta o alguna dependencia de inferencia.

### `weak`

Evidencia debil significa que la interpretacion depende de proxy, proveedor
controlado, datos demo, evidencia externa general o cobertura incompleta. Sirve
para priorizar curacion, no para sostener una conclusion biologica fuerte.

### `insufficient`

Evidencia insuficiente significa que faltan datos criticos, la cobertura es muy
baja, la confianza es baja o solo existe plantilla/demo sin trazabilidad
suficiente.

## Relacion con procedencia

- `source_quality` resume la calidad asignada por tipo de fuente.
- `data_realism_flag=demo_only` degrada la fuerza interpretativa.
- Las columnas `*_is_proxy` y `proxy_feature_count` identifican inferencia
  indirecta.
- `data_user/` y capas organism-specific aumentan fuerza solo si estan
  trazadas y completas.
- Cache no aumenta por si misma la calidad biologica, pero mejora
  reproducibilidad.

## Reporte generado

Cuando se exportan resultados se genera:

- `results/evidence_strength_audit.csv`
- `results/evidence_strength_audit.md`

Columnas principales:

- `evidence_strength`
- `evidence_strength_reason`
- `evidence_coverage_summary`
- `weak_evidence_flags`
- `strong_evidence_flags`

Estas columnas son interpretativas. No modifican `meta_priority_score`,
`therapeutic_priority_score`, `ranking_nodos.csv` ni la seleccion de top
candidatos.

## Uso en reportes o manuscritos

Describe el ranking como priorizacion computacional exploratoria. Reporta el
score junto con la fuerza de evidencia y las banderas debiles. Evita afirmar
validacion terapeutica si `evidence_strength` es `weak` o `insufficient`, aunque
el score sea alto.
