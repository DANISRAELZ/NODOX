# Curated Snapshots

## Proposito

Un snapshot curado es una referencia pequena, versionada y auditable que describe un conjunto estable de evidencias y procedencia para un organismo. No es una corrida del pipeline, no es un cache vivo y no reemplaza datos de usuario.

El primer snapshot creado es:

```text
data_external/curated_snapshots/pseudomonas_aeruginosa_pao1/
```

## Por que PAO1 primero

`Pseudomonas aeruginosa` PAO1 ya tiene validacion controlada documentada para STRING/UniProt y un ranking demo estable. Por eso es un buen organismo inicial para validar contratos de snapshot sin hacer llamadas online frescas.

Este snapshot PAO1 es `controlled_demo_reference`: sirve para probar estructura, procedencia y reproducibilidad. No afirma que sus ejemplos pequenos sean un catalogo biologico completo.

## Diferencias importantes

| Elemento | Que es | Se versiona |
| --- | --- | --- |
| Snapshot curado | Referencia pequena y congelada con metadata, manifiesto de fuentes y procedencia. | Si, bajo `data_external/curated_snapshots/`. |
| Cache | Resultado reutilizable de proveedores o resolucion local. Puede quedar obsoleto. | No como cache volatil completo. |
| Workspace | Carpeta de ejecucion bajo `data_sessions/` con outputs generados. | No como snapshot curado. |
| Output generado | Ranking, reportes y tablas producidas por una corrida. | Solo referencias pequenas seleccionadas, nunca carpetas completas. |

## Estructura PAO1

```text
data_external/curated_snapshots/
  pseudomonas_aeruginosa_pao1/
    snapshot_metadata.json
    taxonomy.json
    sources_manifest.json
    string_evidence.json
    uniprot_evidence.json
    functional_annotations.json
    provenance.json
    README.md
```

## Contrato de `snapshot_metadata.json`

Campos obligatorios:

- `schema_version`
- `organism`
- `strain`
- `canonical_organism_name`
- `taxon_id`
- `snapshot_id`
- `snapshot_label`
- `created_at_utc`
- `acquisition_mode`
- `network_policy`
- `allowed_sources`
- `source_versions`
- `cache_policy`
- `evidence_status`
- `confidence_policy`
- `provenance_policy`
- `limitations`
- `generated_by`
- `reproducibility_notes`

Para PAO1, `network_policy` queda en `no_fresh_network_calls` y `acquisition_mode` en `curated_snapshot_offline`.

## Contrato de `sources_manifest.json`

Cada fuente debe declarar:

- `source_name`
- `source_type`
- `source_status`
- `retrieval_status`
- `acquisition_mode`
- `cache_status`
- `confidence`
- `evidence_kind`
- `is_stub`
- `is_controlled`
- `is_real_external`
- `date_accessed_utc`
- `source_url`
- `source_reference`
- `notes`

Reglas de interpretacion:

- Evidencia real externa: puede estar referida como cache congelado, pero no como llamada fresca en esta fase.
- Evidencia controlada: debe marcar `is_controlled=true` y `is_real_external=false`.
- Stub: debe marcar `is_stub=true` y no presentarse como evidencia real.
- Fallback: debe conservar notas de procedencia y no contar como evidencia biologica.
- Cache: debe diferenciar `cache_reuse_run` de `controlled_fixture`.

## Validacion offline

El modulo `src/nodos_funcionales/curated_snapshots.py` valida:

- campos obligatorios;
- contradicciones entre `is_stub`, `is_controlled` e `is_real_external`;
- uso indebido de `fresh_api_run` en snapshots offline;
- fuentes controladas marcadas como API fresca;
- fallback sin notas;
- cache reutilizado confundido con fixture controlado.

Comando:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest tests/test_curated_snapshots.py -q
```

## Que no se versiona

- payloads crudos descargados de STRING o UniProt;
- caches volatiles completos;
- carpetas `data_sessions/` generadas;
- rankings nuevos no curados;
- archivos privados, clinicos, propietarios o no publicables.

## Extension futura

La siguiente expansion debe crear snapshots reales curados, en commits separados, para:

- `Corynebacterium pseudotuberculosis`: primero definir cepa, taxon id y fuentes autorizadas.
- `Mycobacterium tuberculosis` H37Rv: usar como validacion cruzada por cobertura publica estable.

Ambos deben mantener la misma separacion entre evidencia externa real, controlada, stub, fallback y cache.
