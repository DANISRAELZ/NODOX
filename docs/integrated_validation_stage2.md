# Stage 2: auditoría específica y ablación evolutiva

## Propósito

Stage 2 transforma el inventario global de Stage 1 en una evaluación específica de una corrida. El caso predeterminado es:

`results/20260805_helicobacter_pylori_online_strict_25_v10g_final_audit`

La etapa no modifica el scoring, los pesos predeterminados ni los resultados históricos.

## Salidas

### Auditoría de la corrida seleccionada

- `selected_run_candidate_audit.csv`
- `selected_run_provider_audit.csv`
- `selected_run_layer_coverage.csv`
- `selected_run_audit_manifest.json`
- `selected_run_audit_report.md`

### Ablación del componente evolutivo

- `evolutionary_ablation_by_candidate.csv`
- `evolutionary_weight_sensitivity.csv`
- `evolutionary_ablation_summary.json`
- `evolutionary_ablation_report.md`

## Escenarios

1. **Modelo completo:** reconstrucción de la fórmula configurada de la Teoría de Nodos Funcionales.
2. **Sin penalización de escape:** elimina únicamente `p_escape`.
3. **Sin dimensión evolutiva:** elimina `w_evolutionary_constraint`, `p_escape`, `p_biofilm` y `p_hgt`. Se conserva `p_redundancy` para no confundir la compensación funcional del Postulado 3 con toda la dimensión evolutiva.
4. **Sensibilidad:** modifica en ±10 % y ±20 % los pesos evolutivos sin cambiar la configuración original.

## Convención de cambio de rango

`rank_shift_full_vs_no_evolutionary_dimension = rango_completo - rango_sin_dimensión_evolutiva`

- valor positivo: el candidato fue despriorizado al añadir la dimensión evolutiva;
- valor negativo: fue promovido;
- cero: no cambió de posición.

## Límites

- La ablación no demuestra que el riesgo de escape prediga resistencia.
- Una variable faltante debe conservarse como desconocida, no como riesgo bajo.
- La presencia de una columna no demuestra evidencia biológica independiente.
- Una discrepancia entre el puntaje reconstruido y el reportado debe resolverse antes de publicar cifras.
