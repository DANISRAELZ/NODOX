# Importacion generica de anotaciones

## Proposito

Nodos Funcionales puede convertir anotaciones locales de cualquier organismo al esquema interno del pipeline. Esta ruta no pertenece a ninguna coleccion particular de aislados ni a ningun proyecto genomico externo.

## Insumos aceptados

Coloca los archivos en un directorio local elegido por el usuario. Nombres reconocidos:

- `prokka.tsv` o `annotations.tsv`
- `gene_presence_absence.csv`
- `vfdb.tsv` o `vfanalyzer.tsv`
- `rgi.txt` o `rgi.tsv`
- `mobileog.tsv`
- `phastest.tsv`
- `alienhunter.txt` o `alienhunter.tsv`
- `string.tsv`
- `uniprot_localization.tsv`
- `literature_support.csv` o `literature_support.tsv`

Los fixtures en `tests/fixtures/generic_organism_annotations/` son datos minimos de prueba. No son evidencia real y no alimentan corridas reales por defecto.

## Ejecucion

```powershell
python import_dataset.py --input-format generic_annotations --workspace data_sessions/organism_demo --input-dir data_raw_annotations/organism_demo --organism "Nombre del organismo"
```

## Capas generadas

- `essentiality.csv`
- `virulence.csv`
- `strain_conservation.csv`
- `functional_network.csv`
- `localization.csv`
- `evolutionary_escape_risk.csv`
- `literature_support.csv`

Si falta una fuente, se crea una tabla vacia con columnas correctas y `provenance_status` igual a `missing_input` o `insufficient_evidence`.

## Regla de evidencia

La ausencia de un archivo o de una anotacion no se interpreta como evidencia negativa. Por ejemplo, no encontrar un gen en una tabla incompleta no significa que el gen no sea esencial, no sea virulento o tenga bajo riesgo evolutivo.
