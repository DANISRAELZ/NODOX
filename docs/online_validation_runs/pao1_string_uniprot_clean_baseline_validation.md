# Validacion PAO1 STRING/UniProt con baseline limpio

## Fecha y alcance

Fecha de ejecucion: 2026-05-06.

Organismo:

- `Pseudomonas aeruginosa`
- Cepa: `PAO1`

Workspace local usado:

```text
data_sessions\pao1_online_optional_clean_baseline_validation
```

Este workspace es local, ignorado por Git y no debe versionarse. Los outputs
online generados se usan solo como evidencia de auditoria.

Commit documental previo relacionado:

```text
5ac0b9a Document PAO1 STRING UniProt online validation closure
```

## Estado inicial

Antes de preparar la validacion:

- `git status --short` estaba vacio.
- Las pruebas `not online` ya habian pasado al 100%.
- El cambio temporal en `config/taxon_resolution_cache.json` habia sido restaurado.

## Causa de la advertencia previa

La advertencia:

```text
baseline_not_clean_non_string_network_preserved
```

se origina en `src/nodos_funcionales/online_audit.py`, dentro de
`_reset_source_layer()`. Para STRING, la condicion se activa cuando existe:

```text
data_raw\functional_network.csv
```

y ese archivo no parece salida directa de STRING segun `provider` o `database`.

En el baseline demo/local se encontro red funcional basal en:

```text
data_raw\functional_network.csv
data_demo\functional_network.csv
data_sessions\pseudomonas_aeruginosa_pao1\data_raw\functional_network.csv
```

Caracteristicas del archivo basal:

- Filas: 10.
- Columnas: `protein_id`, `gene`, `network_centrality`,
  `pathway_bottleneck_score`, `redundancy_penalty`,
  `functional_dependency_score`, `database`.
- `database`: `example_curated_demo`.
- Tipo de evidencia: demo/curada de ejemplo, no STRING fresco.

Por eso el auditor la preservo de forma conservadora y marco que el baseline no
estaba completamente libre de red funcional no STRING.

## Preparacion del baseline limpio

Se creo un workspace separado con el demo PAO1 en modo offline:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --workspace data_sessions\pao1_online_optional_clean_baseline_validation --taxon-resolution-mode offline_only
```

Luego, solo dentro del workspace local, se preparo un baseline limpio:

- `config\params.yaml` del workspace se ajusto a
  `online_sources.source_mode_default: offline_only`.
- Se eliminaron del workspace:
  - `data_raw\functional_network.csv`
  - `data_processed\validated_functional_network.csv`
  - `data_processed\normalized_functional_network.csv`
  - `data_external\functional_network.csv`
  - `data_cache\functional_network.csv`
  - `config\string_network_cache.json`

Verificacion antes de auditar:

- No existia red funcional basal en `data_raw`, `data_external` ni `data_cache`
  del workspace limpio.
- El pipeline interno del auditor no podia reinyectar red por capa externa
  durante el baseline, porque el config local estaba en `offline_only`.

## Cache controlado

Para que los escenarios cache fueran cache real y no otra llamada fresca, se
sembraron caches locales dentro del workspace con llamadas online controladas:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe fetch_online_data.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_optional_clean_baseline_validation --source string --mode online_optional --refresh-online-cache --replace-existing-functional-network --skip-pipeline-rerun
```

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe fetch_online_data.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_optional_clean_baseline_validation --source uniprot --mode online_optional --refresh-online-cache --skip-pipeline-rerun
```

Los archivos crudos generados por esas llamadas quedaron marcados como outputs
reconocibles de proveedor (`computed_string_api_v1`, `string_db`,
`computed_uniprot_api_v1`) y fueron removidos por el auditor en los clones antes
de construir cada baseline.

## Auditoria ejecutada

Comando:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_optional_clean_baseline_validation --sources string uniprot --mode online_optional --compare
```

Escenarios auditados:

1. `baseline_no_online`
2. `string_only_fresh`
3. `uniprot_only_fresh`
4. `combined_online_fresh`
5. `string_only_cache`
6. `uniprot_only_cache`
7. `combined_online_cache`

Archivos generados dentro del workspace:

- `results\online_source_fresh_audit.csv`
- `results\online_source_fresh_audit.md`
- `results\online_source_fresh_vs_cache.csv`
- `results\online_source_fresh_vs_cache.md`
- `results\online_source_candidate_shifts_fresh.csv`

Estos outputs no se versionan.

## Resultado de limpieza

La advertencia previa desaparecio.

Todos los escenarios registraron:

```text
reset_status=clean_reset_applied
```

No aparecio:

```text
baseline_not_clean_non_string_network_preserved
```

Interpretacion: el baseline usado por los clones quedo libre de red funcional
basal no atribuible a STRING. Cuando habia archivos crudos sembrados para cache,
el auditor los reconocio como outputs de proveedor y los removio antes de
construir el baseline.

## Resultados por fuente

### STRING

Escenario fresh:

- `run_kind`: `fresh_api_run`.
- `api_attempted`: `True`.
- `api_success`: `True`.
- `features_changed_count`: 42.
- `scores_changed_count`: 4.
- `ranking_changed`: `True`.
- `top10_changed`: `True`.
- `impact_status`: `top10_level_effect`.
- `causal_reading`: `fresh_effect_confirmed`.
- Estrategia impactada: `functional_node_score`.
- Candidato con mayor desplazamiento: `PA0007`, delta de ranking 2.
- Top candidate antes/despues: `PA0008` / `PA0008`.
- Top score antes/despues: `0.6924931750000001` /
  `0.7050592489999999`.

Scores modificados:

- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`

Interpretacion: con baseline limpio, STRING sigue produciendo un efecto
reproducible a nivel Top 10/ranking/scores. Esto refuerza que el efecto observado
no dependia de la red demo `example_curated_demo` preservada en la validacion
anterior.

### UniProt

Escenario fresh:

- `run_kind`: `fresh_api_run`.
- `api_attempted`: `True`.
- `api_success`: `True`.
- `features_changed_count`: 0.
- `scores_changed_count`: 0.
- `ranking_changed`: `False`.
- `top10_changed`: `False`.
- `impact_status`: `no_detectable_effect`.

Interpretacion: en este baseline limpio, UniProt no produjo cambios detectables
en features, scores ni ranking. Esto es mas estricto que la corrida previa, donde
UniProt se habia interpretado como efecto a nivel features.

### STRING+UniProt

Escenario fresh combinado:

- `run_kind`: `mixed_run`.
- Componentes: `fresh_api_run;fresh_api_run`.
- `features_changed_count`: 42.
- `scores_changed_count`: 4.
- `ranking_changed`: `True`.
- `top10_changed`: `True`.
- `impact_status`: `top10_level_effect`.

Interpretacion: el efecto combinado reproduce el efecto de STRING. No se observo
un efecto adicional atribuible a UniProt en esta corrida.

## Comparacion fresh vs cache

STRING:

- Fresh: `fresh_api_run`, `top10_level_effect`, 4 scores modificados.
- Cache: `cache_reuse_run`, `top10_level_effect`, 4 scores modificados.
- Etiqueta comparativa: `fresh_effect_confirmed`.

UniProt:

- Fresh: `fresh_api_run`, `no_detectable_effect`.
- Cache: `cache_reuse_run`, `no_detectable_effect`.
- Etiqueta comparativa: `no_detectable_effect`.

STRING+UniProt:

- Fresh: `mixed_run`, `top10_level_effect`, 4 scores modificados.
- Cache: `mixed_run`, `top10_level_effect`, 4 scores modificados.
- Etiqueta comparativa: `fresh_effect_confirmed`.

Interpretacion: cache reproduce el efecto de STRING y del combinado. UniProt no
produce efecto detectable ni fresco ni cacheado.

## Interpretacion causal

Se puede afirmar:

- La advertencia `baseline_not_clean_non_string_network_preserved` fue eliminada.
- El efecto de STRING persiste con baseline limpio.
- El efecto de STRING se reproduce desde cache local controlado.
- En esta corrida, UniProt no explica cambios de ranking, Top 10 ni scores.
- El efecto combinado STRING+UniProt esta dominado por STRING.

No se puede afirmar:

- Que STRING sea evidencia curada o validada experimentalmente para priorizacion
  clinica final.
- Que UniProt carezca de valor biologico general; solo no produjo efecto
  detectable en esta configuracion y conjunto PAO1.
- Que los resultados online frescos deban convertirse en snapshot curado.

Pendiente:

- Revisar por que los mappings STRING devuelven identificadores/preferred names
  que no siempre coinciden con el gen de entrada.
- Mantener separadas evidencia fresca, cacheada, curada, fallback, stub, missing,
  ausencia de evidencia y evidencia negativa real.

## Pruebas posteriores

Comando ejecutado:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Resultado:

- Pruebas `not online`: pasaron al 100%.
- Warnings aceptados: `RuntimeWarning` conocido de Phase 3 cuando el ranking
  contiene solo candidatos demo/template o missing.

## Estado final de Git

Despues de las pruebas, `config/taxon_resolution_cache.json` volvio a cambiar
solo por:

- `updated_at_utc`
- `saved_at_utc`
- `refresh_count`

Ese cache fue restaurado. La documentacion de este cierre es el unico cambio que
debe versionarse.
