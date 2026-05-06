# Cierre de validacion online_optional controlada: PAO1 STRING/UniProt

## Estado

Validacion cerrada y documentada. La corrida se ejecuto como auditoria
controlada `online_optional` en un workspace separado, sin versionar outputs
generados dentro de `data_sessions`.

Commit relacionado:

```text
08f7e50 Track online source workflow and validation audit.
```

Pruebas:

- Las pruebas `not online` pasaron al 100%.
- Despues de la validacion, `git status --short` quedo limpio antes de iniciar
  esta actualizacion documental.

## Workspace usado

```text
data_sessions\pao1_online_optional_validation_04052026
```

Los resultados de este workspace se consideran evidencia local de auditoria.
No deben convertirse en snapshots versionados ni mezclarse con los outputs
legacy/modulares principales sin una decision explicita de curacion.

## Escenarios auditados

Se auditaron 7 escenarios:

- `baseline_no_online`
- `string_only_fresh`
- `uniprot_only_fresh`
- `combined_online_fresh`
- `string_only_cache`
- `uniprot_only_cache`
- `combined_online_cache`

## Archivos generados

Dentro del workspace de validacion se generaron:

- `results/online_source_fresh_audit.csv`
- `results/online_source_fresh_audit.md`
- `results/online_source_fresh_vs_cache.csv`
- `results/online_source_fresh_vs_cache.md`
- `results/online_source_candidate_shifts_fresh.csv`

Estos archivos no se versionan. Se documenta solo el resultado resumido de la
validacion.

## Resultado principal

- STRING produjo efecto a nivel Top 10, cambio el ranking y modifico 4 scores.
- UniProt produjo efecto a nivel de features, sin cambiar ranking ni scores.
- STRING+UniProt reprodujo el efecto observado con STRING.
- Fresh y cache fueron consistentes en la comparacion controlada.

Interpretacion:

- El efecto principal de la validacion online provino de STRING.
- UniProt aporto cambios de anotacion/feature sin impacto estrategico directo
  sobre scores ni ordenamiento en esta corrida.
- La consistencia fresh/cache indica que el cache local reproduce el efecto
  observado para las fuentes auditadas en este workspace.

## Limitacion registrada

En escenarios con STRING aparece:

```text
baseline_not_clean_non_string_network_preserved
```

Esto indica que el baseline conservaba algun componente de red no STRING o
estado previo no completamente limpio. La lectura del efecto STRING sigue siendo
util para auditoria controlada, pero requiere una corrida futura con baseline
completamente limpio para cerrar la interpretacion causal sin esa advertencia.

## Regla de cierre

No convertir datos online no curados en evidencia real permanente ni en snapshot
de referencia. La evidencia fresca, cacheada, curada, fallback y ausencia de
evidencia deben seguir separadas en futuros commits.
