# Therapeutic Priority Decomposition Phase

## Proposito cientifico

Esta fase refuerza la interpretabilidad de la expansion terapeutica. El pipeline
ya calculaba `therapeutic_priority_score`; ahora tambien exporta cuanto aporta
cada variable al score final para que el ranking pueda auditarse sin recalcular
manualmente las ponderaciones.

El cambio no modifica la formula de priorizacion. Solo materializa la
descomposicion del score en columnas explicitas y en un resumen legible por
candidato.

## Variables nuevas

- `therapeutic_priority_meta_priority_score_contribution`
- `therapeutic_priority_host_safety_score_contribution`
- `therapeutic_priority_host_damage_score_contribution`
- `therapeutic_priority_infection_site_access_score_contribution`
- `therapeutic_priority_infection_context_score_contribution`
- `therapeutic_priority_contribution_summary`

Cada contribucion representa el valor normalizado de la variable multiplicada
por su peso configurado en `therapeutic_phase1.priority_weights`.

## Reglas de scoring

La formula base sigue siendo:

```text
therapeutic_priority_score =
  weighted_mean(
    meta_priority_score,
    host_safety_score,
    host_damage_score,
    infection_site_access_score,
    infection_context_score
  )
```

Las nuevas columnas dividen esa media ponderada en partes auditables. La suma de
las columnas `therapeutic_priority_*_contribution` debe coincidir con
`therapeutic_priority_score`, salvo redondeos de salida.

## Limitaciones actuales

- La descomposicion explica el score numerico, no valida la evidencia biologica
  de cada variable.
- Si una variable proviene de proxy o proveedor controlado, su contribucion
  sigue marcada por las banderas y auditorias ya existentes.
- La interpretacion depende de los pesos actuales de `config/params.yaml`.

## Pasos futuros sugeridos

1. Anadir una vista compacta por rol terapeutico mostrando los principales
   componentes que dominan cada grupo.
2. Separar la explicacion para usuarios no tecnicos de la auditoria tecnica
   completa.
3. Usar esta descomposicion para detectar candidatos cuyo ranking depende de
   una sola capa incompleta o controlada.
