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

La estructura de fuentes curadas se documenta en `docs/curated_snapshots.md`. Los snapshots de esta pagina siguen enfocados en estabilidad del ranking; los snapshots curados bajo `data_external/curated_snapshots/` describen fuentes, procedencia y contratos de evidencia.

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
    pseudomonas_aeruginosa_pao1/
      snapshot_manifest.yaml
      source_manifest.csv
      checksums.sha256
      ranking_reference.csv
    corynebacterium_pseudotuberculosis/
      snapshot_manifest.yaml
      source_manifest.csv
      checksums.sha256
      ranking_reference.csv
    mycobacterium_tuberculosis_h37rv/
      snapshot_manifest.yaml
      source_manifest.csv
      checksums.sha256
      ranking_reference.csv
```

### Candidatos propuestos

No se crean todavia snapshots reales falsos. Candidatos razonables cuando existan datos autorizados:

- `Pseudomonas aeruginosa` PAO1 con fuentes externas cacheadas/controladas y revisadas.
- `Mycobacterium tuberculosis` H37Rv.
- `Corynebacterium pseudotuberculosis` como ejemplo generico, solo con datos curados, autorizados y cargados explicitamente por el usuario.

### Manifest minimo de snapshot curado

Cada `snapshot_manifest.yaml` debe registrar, como minimo:

```yaml
organism: "Pseudomonas aeruginosa"
strain: "PAO1"
taxon_id: "208964"
acquisition_date: "YYYY-MM-DD"
acquisition_mode: "curated_snapshot_offline"
string_source:
  provider: "STRING"
  mode: "cache_first|online_optional_then_frozen"
  cache_status: "cache_hit|frozen_cache|not_used"
  confidence: 0.0
uniprot_source:
  provider: "UniProt"
  mode: "cache_first|online_optional_then_frozen"
  cache_status: "cache_hit|frozen_cache|not_used"
  confidence: 0.0
evidence_status: "demo|curated_reference|real_external_frozen|mixed_with_controlled"
provenance: "short human-readable provenance summary"
limitations:
  - "Document what is incomplete or not comparable."
checksums:
  source_manifest_csv: "sha256:<hash>"
  ranking_reference_csv: "sha256:<hash>"
```

`source_manifest.csv` debe ser tabular para revision rapida y contener una fila por fuente/capa:

```text
organism,strain,taxon_id,layer,source_name,source_type,acquisition_date,acquisition_mode,cache_status,evidence_status,confidence,provenance,limitation_note,checksum
```

### Snapshots iniciales por organismo

| Organismo | Cepa | Taxon id esperado | Rol del snapshot | Estado recomendado |
| --- | --- | --- | --- | --- |
| `Pseudomonas aeruginosa` | PAO1 | `208964` para cepa PAO1, `287` para especie cuando aplique | Demo controlado y validacion de cierre STRING/UniProt | Preparar primero como snapshot congelado desde cache/documentacion ya validada, sin nueva red. |
| `Corynebacterium pseudotuberculosis` | Definir cepa curada antes de congelar | Depende de cepa o especie seleccionada | Organismo real prioritario del proyecto | Requiere manifest curado y decision explicita de cepa antes de crear referencia. |
| `Mycobacterium tuberculosis` | H37Rv | `83332` para H37Rv, `1773` para especie cuando aplique | Validacion cruzada real | Usar como segundo control real porque tiene mejor cobertura publica esperada. |

Para evitar mezclar datos, cada snapshot debe indicar si el `taxon_id` corresponde a especie o cepa. Si STRING o UniProt usan distinto nivel taxonomico, el manifest debe explicarlo en `limitations`.

### Reglas antes de versionar un snapshot real

- No ejecutar red durante la creacion de esta fase documental.
- No versionar caches volatiles completas.
- Versionar solo referencias pequenas y revisadas humanamente.
- Separar el commit de datos curados del commit de cambios de codigo.
- Calcular checksums despues de congelar los CSV.
- No mezclar snapshots demo con reales en el mismo archivo.

### Privacidad y reproducibilidad

No subir snapshots reales si contienen datos privados, clinicos sensibles, propietarios o no publicables. No mezclar datos demo con datos reales sin marcarlo explicitamente.
