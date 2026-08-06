# Stage 2.1 — Separación entre riesgo respaldado, proxy y desconocido

## Objetivo

Esta etapa corrige la interpretación de la ablación evolutiva sin modificar
las fórmulas, pesos ni resultados históricos de NODOX.

La salida distingue tres escenarios:

1. `ranking_without_evolutionary_information`: elimina la dimensión evolutiva.
2. `ranking_with_proxy_evolutionary_score`: reproduce la formulación derivada
   actual y se interpreta únicamente como hipótesis exploratoria.
3. `ranking_with_supported_evolutionary_score`: aplica la dimensión evolutiva
   sólo a candidatos que superan el umbral de variables explícitas.

## Regla conservadora

Por defecto se requieren al menos tres variables evolutivas explícitas y un
estado diferente de `unknown`, `missing`, `not_reported`, `unresolved`,
`insufficient_evidence` o `derived_from_related_layers`.

Un valor numérico con procedencia `missing`, `derived` o `proxy` no se convierte
en evidencia respaldada. En particular, `0.0` con fuente `missing` no se
interpreta como ausencia biológica de redundancia o escape.

## Nuevas salidas

- `evolutionary_ablation_by_candidate.csv`
- `evolutionary_ablation_by_gene.csv`
- `evolutionary_proxy_decomposition.csv`
- `evolutionary_weight_sensitivity.csv`
- `evolutionary_ablation_summary.json`
- `evolutionary_ablation_report.md`

## Alcance científico

La etapa demuestra operacionalización, trazabilidad y sensibilidad del ranking.
No demuestra predicción de resistencia, eficacia terapéutica ni validación
experimental del riesgo de escape.
