# Builder de entradas terapéuticas curadas

## Propósito científico

Las colas de curación terapéutica ayudan a revisar candidatos, pero no deben entrar al pipeline hasta que una persona complete evidencia trazable. El builder convierte únicamente filas completas en CSV compatibles con la arquitectura actual.

No calcula scores, no inventa evidencia faltante y no consulta internet. Su función es transformar curación manual revisada en archivos que el resolvedor ya puede consumir.

## Entradas

El script lee, cuando existen:

```text
results/clinical_impact_curation_queue.csv
results/disease_context_curation_queue.csv
results/therapy_site_context_curation_queue.csv
```

Solo utiliza columnas `curated_*`. Las columnas `current_*` son contexto y no reemplazan evidencia manual.

## Salidas

Para datos revisados por el usuario:

```text
data_user/clinical_impact.csv
data_user/curated_disease_context.csv
data_user/therapy_site_context.csv
```

Para catálogos externos curados:

```text
data_external/curated_catalogs/clinical_impact/<catalog_key>.csv
data_external/curated_catalogs/curated_disease_context/<catalog_key>.csv
data_external/curated_catalogs/therapy_site_context/<catalog_key>.csv
```

La resolución mantiene prioridad para `data_user/`. Los catálogos externos son artefactos reproducibles y deben conservar procedencia.

## Reglas de inclusión

Una fila solo se materializa cuando están completos los campos curados requeridos para su capa, incluidos scores, tipo de evidencia y referencia trazable. Los scores deben permanecer entre `0.0` y `1.0`.

## Uso portable

Crear archivos en `data_user/`:

```powershell
python scripts/build_curated_therapeutic_inputs.py --workspace data_sessions/pseudomonas_aeruginosa_pao1 --target data_user
```

Crear un catálogo externo:

```powershell
python scripts/build_curated_therapeutic_inputs.py --workspace data_sessions/pseudomonas_aeruginosa_pao1 --target external_catalog --catalog-key taxon_287
```

Reemplazar archivos existentes de forma explícita:

```powershell
python scripts/build_curated_therapeutic_inputs.py --workspace data_sessions/pseudomonas_aeruginosa_pao1 --target data_user --overwrite
```

En un entorno virtual también puede usarse `python` después de activarlo o la ruta relativa del intérprete, por ejemplo `./.venv/Scripts/python.exe` en Windows.

## Limitaciones

- El builder valida estructura, no validez biológica de una referencia.
- No fusiona con archivos existentes; el reemplazo requiere `--overwrite`.
- No cambia el ranking hasta que se ejecute nuevamente el pipeline.
- Los catálogos deben conservar fuente, fecha, versión y limitaciones.
