# First User-Curated Dataset Startup

## Proposito

Este documento describe el procedimiento controlado para iniciar el primer
dataset real `user_curated` en una carpeta local ignorada por Git. La meta es
organizar datos, manifest, README, procedencia y notas antes de cualquier
importacion, sin versionar datos reales y sin ejecutar pipeline ni scoring.

Esta fase no produce outputs versionados. Solo prepara una carpeta local de
trabajo bajo `user_curated_staging/<project_id>/`.

## Primer organismo recomendado

Puede usarse cualquier organismo bacteriano. Para el primer intento, elegir un
dataset pequeno, bien curado y facil de auditar. Es preferible empezar con pocas
capas claras antes que mezclar muchas fuentes incompletas.

Usar placeholders hasta tener el organismo real confirmado:

```text
<organism_name>
<strain_or_isolate>
```

No usar organismos de ejemplo como defaults. Evitar copiar residuos de ejemplos,
pruebas, cache o plantillas al manifest real.

## 1. Elegir `project_id`

Elegir un identificador local simple para la carpeta de staging. Debe ser un
nombre de carpeta, no una ruta.

Recomendado:

```text
<project_id>
```

No usar `..`, barras, rutas absolutas ni nombres que puedan confundirse con una
fuente demo, proxy, cache, online o `controlled_reference`.

## 2. Crear staging local

Desde la raiz del repositorio:

```powershell
.\.venv\Scripts\python.exe scripts\create_user_curated_staging.py <project_id>
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

La carpeta `user_curated_staging/` esta ignorada por Git. Esta ubicacion es para
trabajo local con datos reales; no debe agregarse al repositorio.

## 3. Revisar contenido creado

Verificar la estructura:

```powershell
Get-ChildItem user_curated_staging\<project_id>
```

Confirmar que existen:

- `README.md`;
- `manifest.csv`;
- `raw_inputs/`;
- `notes/`;
- `provenance/`.

Si la carpeta ya existe, el scaffold debe detenerse sin sobrescribir archivos.
Revisar manualmente antes de borrar o recrear cualquier contenido local.

## Antes de copiar datos reales

Antes de mover o copiar cualquier archivo real:

- confirmar que la carpeta esta dentro de `user_curated_staging/`;
- confirmar que `git status --short` no muestra los archivos reales;
- confirmar que no hay datos sensibles en rutas versionadas;
- confirmar que el manifest usara `source_type=user_curated`;
- confirmar que los archivos no son demo, proxy, cache, online ni
  `controlled_reference`;
- confirmar que los datos pueden describirse con procedencia trazable.

Comando recomendado:

```powershell
git status --short
```

Si Git muestra archivos reales o sensibles, detenerse y moverlos a una ruta
ignorada antes de continuar.

## 4. Llenar `README.md`

Editar la copia local:

```text
user_curated_staging/<project_id>/README.md
```

Completar, al menos:

- `project_id`;
- `organism`;
- `strain_or_isolate`;
- `curator`;
- `date_created`;
- `manifest_path`;
- `raw_inputs_summary`;
- `provenance_summary`;
- `excluded_or_missing_data`;
- `validation_status`;
- `notes`.

No pegar datos sensibles en el README. Usarlo para resumir alcance, archivos,
procedencia y estado de revision.

## 5. Llenar `manifest.csv`

Editar:

```text
user_curated_staging/<project_id>/manifest.csv
```

Mantener las columnas de la plantilla y reemplazar todos los placeholders. Cada
archivo real debe tener una fila. Para evidencia real revisada por el usuario,
usar:

```text
source_type=user_curated
```

Completar procedencia, esquema esperado, estado de evidencia y notas de
faltantes o limites. No mezclar en el manifest datos demo, proxy, cache, online
o `controlled_reference` como si fueran evidencia real.

## 6. Colocar archivos reales

Colocar archivos reales solo dentro de:

```text
user_curated_staging/<project_id>/raw_inputs/
```

No copiarlos a `docs/`, `data_templates/`, `data_demo/`, `results/`,
`data_processed/`, `data_sessions/` ni snapshots versionados.

Despues de copiar archivos reales, revisar:

```powershell
git status --short
```

La carpeta de staging no debe aparecer como archivo rastreable.

## 7. Documentar procedencia

Guardar referencias, versiones de herramientas, citas, resumen de export o
notas de origen en:

```text
user_curated_staging/<project_id>/provenance/
```

La procedencia debe permitir explicar de donde salio cada archivo sin depender
de memoria oral. Si una evidencia es inferida, incompleta o debil, marcarlo en
el manifest y en las notas.

## 8. Agregar notas de curacion

Guardar decisiones manuales en:

```text
user_curated_staging/<project_id>/notes/
```

Usar esta carpeta para faltantes, exclusiones, conflictos, limites de alcance y
decisiones pendientes. No convertir faltantes o inferencias en evidencia fuerte.

## 9. Prevalidar manifest

Validar con CLI Python:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py user_curated_staging\<project_id>\manifest.csv
```

Validar con wrapper PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 user_curated_staging\<project_id>\manifest.csv
```

La prevalidacion solo revisa estructura minima y separacion de procedencia. No
valida biologicamente el dataset ni confirma valor clinico.

## 10. Importacion prevalidada

Despues de revision manual y prevalidacion del manifest, puede prepararse una
importacion controlada por capa:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "<organism_name>" --strain "<strain_or_isolate>" --workspace <workspace_temporal_o_dedicado> --dataset <dataset> --input user_curated_staging\<project_id>\raw_inputs\<archivo_real.csv> --validate-user-curated-manifest user_curated_staging\<project_id>\manifest.csv
```

Usar un workspace temporal o dedicado. Esta fase todavia no ejecuta pipeline ni
scoring.

## 11. Verificar Git

Antes y despues de editar staging:

```powershell
git status --short
```

El staging local y sus archivos reales no deben aparecer. Si aparecen, detenerse
y corregir la ubicacion antes de continuar.

## Detenerse antes de pipeline/scoring

No ejecutar:

- `run_pipeline.py`;
- Snakemake;
- scoring;
- consultas online como parte de esta fase;
- scripts que escriban reportes finales.

La siguiente decision debe ser una revision manual de manifest, archivos,
procedencia, faltantes y limites interpretativos.

## No avanzar si

Detener el flujo si:

- el manifest no valida;
- hay archivos reales visibles para Git;
- faltan referencias o procedencia;
- hay mezcla con demo, proxy, cache, online o `controlled_reference`;
- se usan defaults de organismos de ejemplo;
- se intenta ejecutar pipeline o scoring antes de revision;
- se pretende interpretar la prevalidacion como validacion biologica,
  terapeutica o clinica;
- hay datos sensibles en rutas versionadas.

## Relacion con otros documentos

- `docs/user_curated_real_dataset_readiness.md`: preparacion general del
  dataset real y staging local.
- `docs/user_curated_operational_flow.md`: flujo desde manifest hasta
  importacion prevalidada.
- `docs/templates/user_curated_staging_README_template.md`: plantilla del
  README local.
- `docs/dataset_import.md`: uso de `import_dataset.py`.
