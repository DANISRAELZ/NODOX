# Curated Snapshots

## Proposito

Un snapshot curado es una referencia pequena, versionada y auditable que describe un conjunto estable de evidencias y procedencia para un organismo. No es una corrida del pipeline, no es un cache vivo y no reemplaza datos de usuario.

En la Teoria de Nodos Funcionales, los snapshots son herramientas de reproducibilidad y validacion tecnica. Sirven para comprobar contratos de capas, procedencia y reportes; no son verdad biologica absoluta ni el centro conceptual del repositorio.

## Multiorganism design principle

Nodos Funcionales esta disenado para priorizar blancos terapeuticos en cualquier organismo bacteriano ingresado por el usuario, siempre que sus capas de evidencia puedan resolverse de forma trazable. PAO1, `Corynebacterium pseudotuberculosis` y H37Rv son casos de referencia; no definen los limites del sistema.

Los snapshots curados son ejemplos congelados para validar contratos, procedencia y reproducibilidad. No son una lista cerrada de organismos soportados. El mismo contrato debe aceptar:

- bacterias con cepa definida;
- bacterias sin cepa definida;
- organismos con `taxon_id` resuelto;
- organismos con `taxon_id` pendiente, si declaran limitaciones explicitas;
- datos aportados por el usuario;
- evidencia externa real validada;
- evidencia controlada/offline;
- evidencia parcial, cacheada, stub o fallback.

Las capas de evidencia deben resolverse por contrato y procedencia, no por reglas especificas de organismo. La ausencia de evidencia externa debe registrarse como `missing`, `not_queried`, `cache_miss`, `stub` o `fallback`, pero nunca interpretarse automaticamente como evidencia biologica negativa.

Cuando no existan fuentes externas completas, el sistema debe aceptar datos de usuario y snapshots controlados, marcando la incompletitud de forma explicita. Cualquier evidencia externa real debe quedar separada de ejemplos controlados y debe conservar `retrieval_status`, `cache_status`, `confidence` y notas de limitacion.

## Snapshots disponibles

El primer snapshot de referencia creado es:

```text
data_external/curated_snapshots/pseudomonas_aeruginosa_pao1/
```

El segundo snapshot extiende el contrato a un organismo adicional usado como ejemplo generico:

```text
data_external/curated_snapshots/corynebacterium_pseudotuberculosis_biovar_ovis/
```

El tercer snapshot agrega una validacion cruzada controlada para H37Rv:

```text
data_external/curated_snapshots/mycobacterium_tuberculosis_h37rv/
```

Estos directorios son fixtures auditables. Nuevos organismos deben poder agregarse sin cambiar el validador si cumplen el mismo contrato.

## PAO1 como baseline tecnico

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

## Corynebacterium pseudotuberculosis Biovar Ovis Controlled Snapshot

Proposito:

- preparar un snapshot curado/controlado para validar el contrato multi-organismo;
- fijar un contrato reproducible antes de validar STRING/UniProt;
- mantener separada la evidencia controlada de la evidencia externa real.

Alcance:

- organismo: `Corynebacterium pseudotuberculosis`;
- biovar: `ovis`;
- strain scope: `generic controlled example`;
- `taxon_id`: `1719`, tomado de `config/taxon_resolution_cache.json`;
- acquisition mode: `controlled_curated_offline`;
- network policy: `no_network`;
- evidence status: `controlled_reference_snapshot`.

Diferencias frente a PAO1:

- PAO1 es demo controlado con validacion STRING/UniProt ya cerrada y documentada.
- Corynebacterium es un ejemplo generico multi-organismo; este snapshot todavia no contiene evidencia online fresca.
- STRING y UniProt aparecen solo como `not_queried_no_network`, con `is_real_external=false`.
- Las anotaciones funcionales son representativas y controladas; validan estructura y procedencia, no ranking.

Archivos:

```text
data_external/curated_snapshots/
  corynebacterium_pseudotuberculosis_biovar_ovis/
    snapshot_metadata.json
    taxonomy.json
    sources_manifest.json
    functional_annotations.json
    provenance.json
    README.md
```

Anotaciones controladas incluidas:

- `pld`
- `dtxR`
- `sodC`
- `fagABCD`
- `hmuTUV`
- `ciuABCDE`
- `gyrA`
- `rpoB`
- `murA`
- `tuf`

Limitaciones:

- no es descarga fresca;
- no representa evidencia online validada en tiempo real;
- no es pangenoma ni viruloma completo;
- no sustituye datos de usuario ni altera scoring;
- no representa una coleccion particular de aislados ni datos de un proyecto externo.

Proximos pasos:

- definir organismo y cepa opcional antes de cualquier refresh externo;
- ejecutar STRING/UniProt solo bajo protocolo `online_optional` controlado;
- congelar manifiestos y checksums despues de revision humana;
- mantener evidencia externa real separada de scaffolds controlados.

## Mycobacterium tuberculosis H37Rv Controlled Snapshot

Proposito:

- validar el contrato de snapshots curados en un tercer organismo bacteriano;
- usar H37Rv como ejemplo multiorganismo controlado, no como acoplamiento del proyecto a tuberculosis;
- mantener separada la evidencia controlada de evidencia online fresca, datos demo, proxy o cache mutable.

Alcance:

- organismo: `Mycobacterium tuberculosis`;
- strain: `H37Rv`;
- `taxon_id`: `83332`;
- acquisition mode: `controlled_curated_offline`;
- network policy: `no_fresh_network_calls`;
- evidence status: `controlled_reference_snapshot`.

Diferencias frente a PAO1 y Corynebacterium:

- PAO1 sigue siendo un demo controlado con validacion STRING/UniProt cerrada y documentada.
- Corynebacterium sigue siendo un ejemplo generico multi-organismo con scaffold controlado offline.
- H37Rv es una validacion cruzada controlada para probar el mismo contrato en otro organismo estable, sin convertirlo en organismo central del proyecto.
- STRING y UniProt aparecen solo como `not_queried_no_network`, con `is_real_external=false`.
- Las anotaciones funcionales son representativas y controladas; validan estructura y procedencia, no ranking.

Archivos:

```text
data_external/curated_snapshots/
  mycobacterium_tuberculosis_h37rv/
    snapshot_metadata.json
    taxonomy.json
    sources_manifest.json
    functional_annotations.json
    provenance.json
    README.md
```

Anotaciones controladas incluidas:

- `rpoB`
- `katG`
- `inhA`
- `embB`
- `gyrA`

Limitaciones:

- no es descarga fresca;
- no representa evidencia online validada en tiempo real;
- no es un catalogo completo de blancos de H37Rv ni una validacion terapeutica;
- no sustituye datos de usuario ni evidencia externa trazable;
- no altera scoring, ranking ni contratos de exportacion;
- la ausencia de genes, capas o variables en este snapshot no equivale a ausencia biologica, bajo riesgo ni irrelevancia terapeutica.

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
- taxonomia con taxon id o limitacion explicita;
- anotaciones funcionales controladas con `source_reference` y `notes`;
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

La siguiente expansion puede profundizar snapshots reales curados, en commits separados, para validar mejor la teoria en ejemplos tecnicos como:

- `Corynebacterium pseudotuberculosis`: pasar del scaffold controlado a evidencia externa validada cuando exista protocolo online.
- `Mycobacterium tuberculosis` H37Rv: pasar del snapshot controlado actual a evidencia externa validada solo si existe un protocolo online explicito y auditable.

Ambos deben mantener la misma separacion entre evidencia externa real, controlada, stub, fallback y cache.
