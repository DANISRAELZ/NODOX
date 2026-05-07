# Validacion de la fase de estabilidad

## Objetivo

Auditar que la fase de estabilidad, trazabilidad y robustez operativa quedo integrada sin romper Fase 1 legacy ni Fase 2 modular.

## Compatibilidad verificada

La corrida demo principal con:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

genero los archivos historicos:

- `results/ranking_nodos_legacy.csv`
- `data_processed/phase2_features.csv`
- `data_processed/scored_nodes.csv`
- `results/ranking_nodos.csv`
- `results/phase_comparison.csv`
- `results/sensitivity_analysis.csv`
- `results/report_phase2.md`
- `results/top10_scientific_audit.csv`
- `results/top10_scientific_audit.md`
- `results/top10_scientific_audit.json`

Tambien genero los reportes nuevos sin reemplazar salidas anteriores:

- `results/candidate_explanations_simple.csv`
- `results/candidate_explanations_simple.md`
- `results/ranking_snapshot.csv`

`results/ranking_snapshot_comparison.csv` se genera solo cuando existe `results/ranking_snapshot_reference.csv`.

## Equivalencia de scoring

Se recalcularon desde `scoring_components.py` las columnas:

- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `preferred_strategy`

Resultado de auditoria sobre el demo PAO1:

- Diferencias numericas maximas: entre `0.0` y `1.11e-16`.
- Diferencias de `preferred_strategy`: `0`.
- Diferencias de ranking contra snapshot de referencia recien generado: `0`.

Interpretacion: las diferencias numericas son ruido de punto flotante y no cambios biologicos ni de ranking.

## Evidencia ausente vs negativa

La evidencia ausente (`missing`, `NaN`, `not_reported`) reduce confianza y genera razones de faltante, pero no se marca como evidencia biologica negativa. La evidencia negativa requiere fuente trazable no demo/no proxy.

Cobertura agregada o confirmada:

- `missing` no activa `evidence_is_negative`.
- valores demo/proxy no activan `evidence_is_negative`.
- homologia humana real externa si puede marcar evidencia negativa.

## Explicaciones simples

`candidate_explanations_simple.*` resume, para usuarios no tecnicos:

- por que un nodo fue priorizado;
- que evidencia lo sostiene;
- que evidencia falta;
- que fuentes se usaron;
- nivel de confianza.

El texto advierte cuando los datos son demo, proxy, cache o controlados, y no los presenta como evidencia externa real.

## Modos online

Los modos quedan normalizados asi:

- `offline_only`: no abre red.
- `local`: alias de `offline_only`, no abre red.
- `api_stub`: alias de `offline_only`, no abre red.
- `cache_first`: modo conservador con cache primero.
- `auto`: alias conservador de `cache_first`.
- `online_optional`: unico modo que permite red y debe degradar trazablemente.

`taxon_resolution_mode` y `online_source_mode` son controles separados. El primero
resuelve el organismo/taxon; el segundo gobierna proveedores externos por capa.
Para evitar el bug operativo observado el 04/05/2026, `--offline-only`,
`--taxon-resolution-mode offline_only`, `local` y `api_stub` fuerzan
`online_source_mode=offline_only` durante `run_pipeline.py`.

Comando PAO1 offline/cache seguro validado:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

Validacion online controlada, solo cuando se desea permitir red:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode cache_first --online-source-mode online_optional
```

Los manifiestos cache-served de STRING y UniProt conservan:

- `source_name`
- `source_version`
- `retrieval_mode`
- `cache_status`
- `provenance`
- `confidence`

## Snapshots de ranking

`ranking_snapshot.csv` es compacto y determinista. Contiene rank, identificadores, scores principales y etiquetas de estrategia/rol.

Para comparar una corrida futura:

```powershell
Copy-Item results\ranking_snapshot.csv results\ranking_snapshot_reference.csv
```

Al ejecutar de nuevo el pipeline, se generara:

- `results/ranking_snapshot_comparison.csv`

con cambios de tipo `added`, `removed`, `rank_changed`, `score_or_label_changed`, `rank_and_score_changed` o `unchanged`.

## Comandos de pruebas recomendados

Unitarias offline:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m unit -q
```

Todas excepto online:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Integracion offline:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m "integration and not online" -q
```

Se recomienda `-p no:cacheprovider` en OneDrive para evitar fallos o demoras al escribir `.pytest_cache`.

## Riesgos restantes

- `online_sources.py` sigue siendo un archivo grande y ya esta rastreado. Conviene dividirlo despues en familias de proveedores, manteniendo una fachada compatible y pruebas de equivalencia.
- Las pruebas online reales no se ejecutaron en esta auditoria; la validacion fue offline/cache-safe.
- Los snapshots de referencia deben curarse y conservarse explicitamente para detectar derivas historicas entre versiones.
