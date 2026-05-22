# Dataset Import

## Propósito

`import_dataset.py` ayuda a convertir exports tabulares del usuario al esquema
interno del workspace sin editar manualmente las columnas una por una.

Para validaciones con datos reales de usuario, usar este importador como apoyo
del protocolo `user_curated` descrito en
`docs/user_curated_validation_protocol.md`. El flujo operativo de preparacion,
prevalidacion e importacion controlada esta descrito en
`docs/user_curated_operational_flow.md`. Para preparar un primer dataset real
en staging local antes de importarlo, ver
`docs/user_curated_real_dataset_readiness.md`; las rutas de staging sugeridas
son locales e ignoradas por `.gitignore`. El importador normaliza columnas,
pero no convierte automaticamente un export en evidencia curada: la procedencia
y la revision biologica deben quedar declaradas por el usuario.

Para una prueba minima controlada con las cuatro capas obligatorias de entrada,
ver `docs/user_curated_minimal_real_dataset.md`.

Para dejar trazabilidad por archivo, completar tambien un manifest basado en
`data_templates/user_curated_dataset_manifest_template.csv`. Ese manifest
describe el dataset, su version, curador, procedencia, esquema de entrada y si
es requerido para scoring; no cambia la logica de importacion ni ejecuta el
pipeline.

## Prevalidar el manifest

Antes de importar datos, puede revisarse la estructura y procedencia minima del
manifest con `validate_user_curated_manifest()`. Esta utilidad no ejecuta el
pipeline, no calcula scores y no valida biologicamente el dataset; solo devuelve
errores de contrato del manifest para decidir si puede avanzar a revision o
importacion.

```python
from pathlib import Path

from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest

manifest_path = Path("path/to/user_curated_dataset_manifest.csv")
errors = validate_user_curated_manifest(manifest_path)

if errors:
    for error in errors:
        print(error)
else:
    print("Manifest listo para revision/importacion.")
```

Una lista vacia significa que el manifest cumple la prevalidacion estructural
minima. No significa que el dataset este aceptado cientificamente ni que pueda
usarse para conclusiones terapeuticas.

La misma revision puede ejecutarse desde consola:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py path\to\user_curated_dataset_manifest.csv
```

En Windows tambien puede usarse el wrapper opcional:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath path\to\user_curated_dataset_manifest.csv
```

El comando devuelve codigo `0` si no hay errores y un codigo distinto de `0` si
el manifest debe corregirse. No llama a `import_dataset.py`, `run_pipeline.py`
ni Snakemake.

Tambien puede pedirse la misma prevalidacion como paso previo explicito dentro
del importador:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --workspace data_sessions/my_organism_workspace --dataset essentiality --input path\to\essentiality.csv --validate-user-curated-manifest path\to\user_curated_dataset_manifest.csv
```

Si el manifest tiene errores, el importador los imprime y se detiene antes de
copiar o normalizar datos. Sin esta bandera, el comportamiento de
`import_dataset.py` permanece igual que antes.

## Uso

```bash
python import_dataset.py --workspace data_sessions/organism_demo --dataset virulence --input exported_virulence.csv
python import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_NAME" --workspace data_sessions/my_organism_workspace --dataset essentiality --input-dir path/to/user_data
```

El primer comando es un ejemplo historico. El importador es multiorganismo y no
depende de un organismo especifico.

## Qué hace

- lee el CSV fuente
- intenta mapear alias frecuentes configurados en `config/params.yaml`
- escribe el archivo normalizado en `workspace/data_raw/<dataset>.csv`
- conserva una copia del export original en `workspace/data_raw/source_exports/`

## Esquema de salida

Para datos `user_curated`, cada CSV debe seguir el template declarado en
`manifest.input_schema`. El archivo normalizado en `data_raw/` conserva solo
columnas contempladas por el dataset interno o mapeadas hacia ese esquema. Una
columna libre del export puede quedar solo en `data_raw/source_exports/` y no
aparecer en la capa interna.

En `essentiality.csv`, la trazabilidad que debe viajar dentro de la capa interna
usa columnas del template como `evidence` y `database`. No usar columnas libres
como `essentiality_score` o `essentiality_call` esperando que se conserven en
`data_raw/essentiality.csv`, salvo que el esquema se amplie formalmente.

## Alias soportados

Ejemplos:

- `locus_tag` -> `protein_id`
- `gene_name` -> `gene`
- `score` -> `virulence_score`
- `vf_flag` -> `virulence_factor`

## Limitación

No intenta inferir semántica compleja ni convertir formatos arbitrarios.
Es un conector semiautomático, no una curación biológica automática.
