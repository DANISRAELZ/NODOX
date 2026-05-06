# Evolutionary Escape Risk

## Objetivo

La subcapa `evolutionary_escape_risk` estima que tan facil podria ser para un patogeno evadir la presion terapeutica sobre un nodo candidato. No reemplaza los scores existentes; agrega una lectura evolutiva auditable y una penalizacion moderada configurable.

## Variables

Todas las variables numericas usan escala 0-1.

| Campo | Interpretacion |
| --- | --- |
| `mutation_tolerance_score` | Alto indica mayor tolerancia mutacional y mayor posibilidad de escape. |
| `functional_redundancy_escape_score` | Alto indica redundancia funcional que podria compensar el bloqueo. |
| `compensatory_pathway_score` | Alto indica rutas alternativas o compensatorias plausibles. |
| `fitness_cost_of_escape` | Alto indica que escapar seria costoso para el patogeno; reduce el riesgo final. |
| `evolutionary_constraint_score` | Alto indica restriccion evolutiva por conservacion, esencialidad, baja redundancia o centralidad. |
| `resistance_emergence_risk` | Riesgo estimado de resistencia especifica contra el blanco. |
| `multi_node_dependency_score` | Alto indica multiples dependencias funcionales simultaneas; reduce el espacio de escape. |
| `evolutionary_escape_risk_score` | Score final: 0 bajo riesgo, 1 alto riesgo. |

## Formula

La formula por defecto es una media ponderada normalizada:

```text
evolutionary_escape_risk_score =
  weighted_mean(
    mutation_tolerance_score,
    functional_redundancy_escape_score,
    compensatory_pathway_score,
    resistance_emergence_risk,
    1 - fitness_cost_of_escape,
    1 - evolutionary_constraint_score,
    1 - multi_node_dependency_score
  )
```

Los pesos viven en `config/params.yaml` bajo `evolutionary_escape_risk.weights`. Si los pesos no suman exactamente 1, el calculo los normaliza entre variables disponibles.

## Penalizacion

El pipeline calcula:

```text
evolutionary_adjusted_meta_priority_score =
  meta_priority_score * (1 - penalty_weight * evolutionary_escape_risk_score)
```

Por defecto `penalty_weight` es `0.15`. Esto penaliza de forma moderada un blanco con alto riesgo evolutivo, pero no lo elimina automaticamente. Para conservar compatibilidad, `meta_priority_score` no se reemplaza salvo que `evolutionary_escape_risk.apply_to_meta_priority` se active explicitamente.

## Robustez evolutiva

Tambien se exportan:

- `evolutionary_robustness_score = 1 - evolutionary_escape_risk_score`
- `reduced_evolutionary_space_score`, que resume restriccion evolutiva, costo fitness, dependencia multinodo y baja compensacion.

Estas columnas ayudan a interpretar candidatos robustos sin cambiar agresivamente el ranking.

## Datos faltantes

Si el usuario aporta `data_user/evolutionary_escape_risk.csv`, esos valores se usan como evidencia explicita. Si faltan variables, el pipeline puede derivar proxies desde capas ya resueltas como conservacion, esencialidad, red funcional o redundancia. Esas derivaciones quedan marcadas como `derived` y reducen la confianza.

Cuando hay poca evidencia explicita:

- `evolutionary_escape_risk_confidence = low`
- `evolutionary_escape_risk_status = insufficient_evidence` o `derived_from_related_layers`
- `evolutionary_escape_risk_missing_variables` lista los campos no aportados por el usuario

Los datos demo se marcan con `source_type=demo` y no deben leerse como evidencia cientifica real.

## Interpretacion

Riesgo bajo no significa prioridad terapeutica alta por si solo: solo indica menor espacio evolutivo estimado. Una prioridad terapeutica alta sigue dependiendo de esencialidad, virulencia, seguridad del hospedero, accesibilidad, contexto infeccioso y calidad de evidencia.

Riesgo alto tampoco descarta automaticamente un blanco. Puede sugerir que el candidato debe evaluarse como blanco secundario, en combinacion terapeutica o con validacion experimental mas estricta.

## Ejemplos

- Riesgo bajo: alto costo fitness, alta restriccion evolutiva, baja redundancia y multiples dependencias funcionales.
- Riesgo moderado: valor terapeutico preservado con senales parciales de compensacion o tolerancia mutacional.
- Riesgo alto: tolerancia mutacional alta, redundancia funcional, rutas alternativas o bajo costo adaptativo.
