# Snapshots curados de ranking

## Proposito

Los snapshots de ranking detectan regresiones pequenas pero importantes sin depender de reportes largos. Sirven para saber si una fase nueva cambio:

- orden del ranking;
- candidatos agregados o removidos;
- scores principales;
- estrategia preferida;
- rol terapeutico.

## Fuente de verdad actual

El primer snapshot curado es demo, no evidencia biologica real:

```text
tests/fixtures/ranking_snapshots/pao1_demo_reference.csv
```

Fue generado desde la corrida demo PAO1 en modo `compare` y se usa como referencia estable para pruebas de regresion.

Columnas esperadas en el snapshot PAO1:

- `rank`
- `protein_id`
- `gene`
- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `therapeutic_priority_score`
- `therapeutic_role`
- `therapeutic_role_rule`
- `preferred_strategy`

No debe incluir timestamps, rutas absolutas ni mensajes variables.

## Archivos generados por pipeline

Cada corrida genera:

```text
results/ranking_snapshot.csv
```

Si existe:

```text
results/ranking_snapshot_reference.csv
```

tambien se genera:

```text
results/ranking_snapshot_comparison.csv
```

## Como actualizar una referencia curada

Actualizar una referencia solo debe hacerse cuando el cambio de ranking este justificado y documentado.

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
Copy-Item data_sessions\pseudomonas_aeruginosa_pao1\results\ranking_snapshot.csv tests\fixtures\ranking_snapshots\pao1_demo_reference.csv
```

## Prueba de snapshot

La prueba marcada como `snapshot` ejecuta la corrida demo PAO1, compara contra la referencia curada y exige que todas las filas queden `unchanged`.

Comando:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m "snapshot and not online" -q
```

## Tolerancia

La comparacion acepta ruido minimo de punto flotante hasta `1.0e-6`. Debe fallar ante:

- cambios de rank;
- nodos agregados;
- nodos removidos;
- cambios en `preferred_strategy`;
- cambios relevantes de score;
- cambios en `therapeutic_role`.

## Snapshots reales controlados

Un snapshot real controlado no es lo mismo que un snapshot demo. El demo PAO1 valida estabilidad del pipeline; un snapshot real controlado valida estabilidad sobre datos curados y trazables.

### Criterios minimos

Antes de aceptar un snapshot real controlado se requiere:

- organismo identificado;
- cepa identificada;
- `taxon_id` o resolucion taxonomica trazable;
- lista de genes/proteinas/nodos;
- anotacion funcional;
- fuente de datos;
- fecha de preparacion;
- modo de ejecucion;
- fuentes externas usadas o explicitamente desactivadas;
- estado de cache;
- version o commit del pipeline;
- revision humana de procedencia/confianza.

### Estructura recomendada

```text
tests/fixtures/ranking_snapshots/
  pao1_demo_reference.csv
  real_controlled/
    README.md
    organism_strain_reference.csv
```

### Candidatos propuestos

No se crean todavia snapshots reales falsos. Candidatos razonables cuando existan datos autorizados:

- `Pseudomonas aeruginosa` PAO1 con fuentes externas cacheadas/controladas y revisadas.
- `Mycobacterium tuberculosis` H37Rv.
- `Corynebacterium pseudotuberculosis` ATCC 19410 o aislados mexicanos, solo con datos curados y autorizados.

### Privacidad y reproducibilidad

No subir snapshots reales si contienen datos privados, clinicos sensibles, propietarios o no publicables. No mezclar datos demo con datos reales sin marcarlo explicitamente.
