# Validación de la fase de estabilidad

## Objetivo

Auditar que la fase de estabilidad, trazabilidad y robustez operativa quedó integrada sin romper las fases previas.

## Ejecución reproducible

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

El organismo se usa como demo controlado. NODOX no está limitado a PAO1.

## Compatibilidad verificada

La corrida conserva las salidas históricas principales y genera reportes adicionales de explicabilidad y snapshot sin reemplazar archivos previos.

Se recalcularon y compararon:

- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `preferred_strategy`

Las diferencias observadas fueron únicamente ruido de punto flotante y no cambios de ranking o interpretación.

## Evidencia ausente frente a negativa

- `missing`, `NaN` y `not_reported` reducen confianza, pero no constituyen evidencia negativa.
- Datos demo o proxy no activan evidencia biológica negativa.
- Una señal negativa requiere una fuente trazable y apropiada.

## Explicaciones

Los reportes simples por candidato resumen:

- razones de priorización;
- evidencia disponible;
- evidencia faltante;
- procedencia;
- nivel de confianza.

Las etiquetas demo, proxy, cache y controlado deben permanecer visibles.

## Modos de ejecución

- `offline_only`: no abre red.
- `cache_first`: prefiere cache.
- `online_optional`: permite red y registra fallos o fallback.
- `api_stub`: valida contratos sin red.

## Resultado

La fase de estabilidad preservó compatibilidad funcional y reforzó trazabilidad, explicabilidad y separación entre ausencia de evidencia y evidencia negativa. Esta validación técnica no constituye validación clínica o experimental.
