# User-Friendly Workflow

## Proposito

Esta guia resume un flujo amigable para preparar, validar e iniciar analisis
con datos reales `user_curated`, sin mezclar demo, proxy, cache, online ni
`controlled_reference`. No cambia la logica cientifica del proyecto ni sustituye
los protocolos detallados.

## 1. Crear un nuevo paquete de datos

Elegir un `project_id` local y crear una carpeta ignorada por Git:

```powershell
.\scripts\new_user_curated_dataset.ps1 -ProjectId <project_id>
```

Esto crea:

```text
user_curated_staging/<project_id>/
  README.md
  manifest.csv
  raw_inputs/
  notes/
  provenance/
```

La carpeta es local. No ejecutar `git add .` sobre datos reales o sensibles.

## 2. Llenar las plantillas

Completar `README.md` y `manifest.csv` dentro de
`user_curated_staging/<project_id>/`. Colocar archivos reales solo en
`raw_inputs/`.

Plantillas utiles:

- `data_templates/functional_annotations_template.csv`
- `data_templates/gene_list_template.csv`
- `data_templates/conservation_template.csv`
- `data_templates/virulence_template.csv`
- `data_templates/essentiality_template.csv`
- `data_templates/external_sources_template.csv`
- `data_templates/manual_curation_template.csv`
- `data_templates/user_curated_dataset_manifest_template.csv`

Usar `source_type=user_curated` solo para evidencia real aportada o revisada por
el usuario. No mezclar filas demo, proxy, cache, online ni
`controlled_reference` como si fueran datos reales.

## 3. Validar antes de ejecutar

Ejecutar:

```powershell
.\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>
```

El validador informa:

- que archivo se esta revisando;
- columnas requeridas faltantes;
- columnas opcionales ausentes;
- valores que parecen placeholders;
- fuentes mezcladas como demo, proxy, cache, online o `controlled_reference`;
- pasos sugeridos para corregir.

Tambien puede validarse solo el manifest:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\<project_id>\manifest.csv
```

## 4. Importar una capa

Despues de revision manual:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -ImportDataset -Dataset <dataset> -InputFile user_curated_staging\<project_id>\raw_inputs\<archivo.csv> -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

El script valida primero el paquete y luego llama a `import_dataset.py` con
`--validate-user-curated-manifest`.

## 5. Ejecutar analisis

Ejecutar pipeline solo despues de revisar manualmente manifest, archivos,
procedencia y faltantes:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -RunPipeline -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

No usar datos demo para una interpretacion real. El script usa modo offline para
taxonomia y no escribe cache taxonomico.

## Errores frecuentes

- Manifest no existe: crear el scaffold o revisar `manifest.csv`.
- Columnas requeridas faltantes: copiar encabezados desde `data_templates/`.
- Columnas opcionales ausentes: documentar el faltante si no aplica.
- Placeholders visibles: reemplazar valores como `<protein_id>` o
  `<source_database>`.
- Archivo no encontrado: colocar el CSV en `raw_inputs/` o corregir
  `input_file`.
- Fuente mezclada: separar demo, proxy, cache, online y `controlled_reference`
  antes de interpretar datos reales.

## Interpretacion

Un `therapeutic_priority_score` alto prioriza una hipotesis computacional, pero
no confirma eficacia ni uso clinico. Si `evidence_confidence_score` es bajo, la
prioridad debe leerse como exploratoria y dependiente de evidencia incompleta.

El riesgo evolutivo ayuda a estimar robustez y posible escape, pero no prueba
que un blanco sea clinicamente seguro o durable. Cualquier conclusion requiere
validacion experimental, revision microbiologica y evaluacion farmacologica o
clinica independiente.
