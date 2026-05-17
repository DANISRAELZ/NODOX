# Dataset Import

## Propósito

`import_dataset.py` ayuda a convertir exports tabulares del usuario al esquema
interno del workspace sin editar manualmente las columnas una por una.

Para validaciones con datos reales de usuario, usar este importador como apoyo
del protocolo `user_curated` descrito en
`docs/user_curated_validation_protocol.md`. El importador normaliza columnas,
pero no convierte automaticamente un export en evidencia curada: la procedencia
y la revision biologica deben quedar declaradas por el usuario.

Para dejar trazabilidad por archivo, completar tambien un manifest basado en
`data_templates/user_curated_dataset_manifest_template.csv`. Ese manifest
describe el dataset, su version, curador, procedencia, esquema de entrada y si
es requerido para scoring; no cambia la logica de importacion ni ejecuta el
pipeline.

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

## Alias soportados

Ejemplos:

- `locus_tag` -> `protein_id`
- `gene_name` -> `gene`
- `score` -> `virulence_score`
- `vf_flag` -> `virulence_factor`

## Limitación

No intenta inferir semántica compleja ni convertir formatos arbitrarios.
Es un conector semiautomático, no una curación biológica automática.
