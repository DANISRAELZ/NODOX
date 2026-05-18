# User-Curated Real Dataset Readiness

## Proposito

Esta guia prepara el primer dataset real `user_curated` antes de importarlo al
workspace de Nodos Funcionales. Su funcion es ordenar archivos, manifest,
notas y procedencia en una carpeta local de trabajo, sin ejecutar scoring,
pipeline ni Snakemake.

La fase llega solo hasta prevalidacion e importacion controlada con
`import_dataset.py --validate-user-curated-manifest`. No produce ranking, no
genera outputs versionados y no convierte evidencia incompleta en evidencia
fuerte.

## 1. Elegir organismo y cepa o aislado

Antes de preparar archivos, definir por escrito:

- organismo bacteriano evaluado;
- cepa, aislado, linaje, conjunto de aislados o alcance taxonomico;
- motivo de inclusion del dataset;
- responsable de curacion;
- fecha o version de la evidencia.

No usar organismos de ejemplo como defaults. PAO1, H37Rv, `Pseudomonas
aeruginosa`, `Mycobacterium tuberculosis` y `Corynebacterium` no deben aparecer
por copia accidental de ejemplos, pruebas, cache o plantillas.

## 2. Crear una carpeta local de staging

Crear una carpeta de trabajo fuera del flujo versionado normal. Esta carpeta es
para organizar datos reales antes de importarlos, no para agregar datos
sensibles al repositorio.

Estructura sugerida:

```text
user_curated_staging/
  <organism_or_project_id>/
    manifest.csv
    raw_inputs/
    notes/
    provenance/
```

Uso recomendado:

- `manifest.csv`: manifest real basado en la plantilla del proyecto.
- `raw_inputs/`: exports, CSVs o tablas reales a revisar.
- `notes/`: decisiones de curacion, faltantes y limites.
- `provenance/`: referencias, versiones de herramientas, citas o descripcion
  de origen.

Esta carpeta es local/de trabajo. No debe versionarse por defecto si contiene
datos reales, privados, clinicos, sensibles o aun no liberados. No ejecutar
`git add .` sobre ella.

## 3. Copiar el manifest template

Copiar la plantilla:

```text
data_templates/user_curated_dataset_manifest_template.csv
```

Ejemplo de copia a staging:

```powershell
Copy-Item .\data_templates\user_curated_dataset_manifest_template.csv .\user_curated_staging\<organism_or_project_id>\manifest.csv
```

Despues de copiarla, reemplazar todos los marcadores de plantilla. El manifest
real debe mantener exactamente las columnas originales:

```text
organism,strain,dataset_id,dataset_version,curator_name,curation_date,source_type,evidence_status,evidence_kind,provenance,input_file,input_schema,required_for_scoring,notes
```

## 4. Llenar el manifest como `user_curated`

Cada archivo real debe tener una fila en el manifest. Usar
`source_type=user_curated` solo si la evidencia fue aportada o revisada por el
usuario para el organismo y alcance declarados.

Completar como minimo:

- `organism`;
- `strain` o alcance equivalente;
- `dataset_id`;
- `dataset_version`;
- `curator_name`;
- `curation_date`;
- `source_type=user_curated`;
- `evidence_status`;
- `evidence_kind`;
- `provenance`;
- `input_file`;
- `input_schema`;
- `required_for_scoring`;
- `notes`.

El campo `input_file` debe apuntar a un archivo existente en staging o a una
ruta clara hacia el archivo que se importara. El campo `provenance` debe
permitir entender de donde salio la evidencia sin depender de memoria oral.

## 5. Listar archivos reales de entrada

Preparar un inventario simple antes de importar. Para cada archivo anotar:

- nombre y ruta;
- capa esperada, por ejemplo `essentiality`, `virulence`, `human_homologs` o
  `localization`;
- plantilla o esquema esperado;
- columnas criticas presentes;
- procedencia y version;
- si contiene datos directos, inferidos, incompletos o proxy marcado;
- si requiere revision manual adicional.

Los archivos reales deben permanecer separados de `data_demo/`, snapshots
`controlled_reference`, cache, proxies y respuestas online frescas.

## 6. Revisar procedencia

Antes de prevalidar, confirmar que cada archivo puede explicarse por una fuente
trazable:

- experimento o medicion;
- export local de una herramienta;
- catalogo o base revisada por el usuario;
- literatura curada;
- anotacion genomica revisada;
- combinacion documentada de fuentes.

Si una fuente es inferida, incompleta o proxy, debe quedar marcada en columnas,
notas o manifest. Cache y online pueden documentarse como contexto, pero no
deben presentarse como evidencia `user_curated` principal en esta fase.

## 7. Revisar campos obligatorios

Antes de ejecutar herramientas, verificar:

- el manifest existe y tiene al menos una fila;
- `organism`, `dataset_id` e `input_file` no estan vacios;
- `source_type` es exactamente `user_curated`;
- no hay marcadores como `<organism_name>` o `<dataset_id>`;
- cada archivo de entrada existe;
- los identificadores principales, como `protein_id` o `gene`, pertenecen al
  organismo declarado;
- cada archivo usa encabezados compatibles con su plantilla o con el importador;
- los limites y faltantes estan documentados.

Para una primera validacion biologica posterior, las capas mas importantes a
preparar son `essentiality`, `virulence`, `human_homologs` y `localization`.
Esta fase, sin embargo, puede detenerse con una sola capa si el objetivo es
probar preparacion e importacion controlada.

## 8. Confirmar separacion de fuentes

No avanzar si los datos reales estan mezclados con:

- demo;
- `controlled_reference`;
- proxy sin marcar;
- cache reutilizado como evidencia nueva;
- online fresco sin fase separada;
- archivos generados por pruebas;
- defaults de organismos de ejemplo.

Si una tabla mezcla fuentes, separarla por archivo o marcar la procedencia por
fila antes de importar.

## 9. Prevalidar con CLI

Ejecutar la prevalidacion estructural del manifest:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py <ruta_manifest.csv>
```

Ejemplo:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py .\user_curated_staging\<organism_or_project_id>\manifest.csv
```

Si aparecen errores, corregir el manifest y repetir la prevalidacion. No
importar datos mientras el manifest falle.

## 10. Prevalidar con wrapper PowerShell

En Windows puede usarse el wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 <ruta_manifest.csv>
```

Ejemplo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 .\user_curated_staging\<organism_or_project_id>\manifest.csv
```

El wrapper llama al mismo validador. Un codigo de salida `0` indica que el
manifest cumple el contrato minimo; un codigo distinto de `0` indica que debe
corregirse.

## 11. Importar con prevalidacion

Cuando el manifest y los archivos pasen revision manual, importar una capa con
prevalidacion opt-in:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace <workspace_temporal_o_dedicado> --dataset <dataset> --input <archivo_real.csv> --validate-user-curated-manifest <ruta_manifest.csv>
```

Ejemplo generico:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace <workspace_temporal_o_dedicado> --dataset virulence --input .\user_curated_staging\<organism_or_project_id>\raw_inputs\virulence.csv --validate-user-curated-manifest .\user_curated_staging\<organism_or_project_id>\manifest.csv
```

Usar un workspace temporal o dedicado para esta primera importacion. No mezclar
la prueba de entrada real con `results/`, `data_processed/`, snapshots,
workspaces historicos ni salidas de fases anteriores.

## 12. Detenerse antes de scoring o pipeline

Despues de la prevalidacion o importacion controlada, detenerse. No ejecutar:

- `run_pipeline.py`;
- Snakemake;
- scoring;
- scripts que generen reportes finales;
- consultas online como parte de esta fase.

La siguiente decision debe ser una revision humana de los archivos importados,
manifest, procedencia y limites interpretativos.

## Control de calidad previo

Aceptar la preparacion para importacion solo si:

- el manifest es valido;
- los archivos existen;
- la procedencia es clara;
- hay evidencia minima suficiente para explicar cada archivo;
- los campos criticos estan completos;
- los limites interpretativos estan aceptados;
- la separacion de fuentes esta revisada;
- una persona acepto manualmente el dataset antes de importar.

## No avanzar si

Detener la fase si:

- faltan archivos;
- hay dudas de procedencia;
- el manifest mezcla demo, proxy o cache como evidencia real;
- se usan organismos de ejemplo como defaults;
- hay evidencia no trazable;
- faltan campos obligatorios del manifest;
- los archivos no corresponden al organismo declarado;
- se pretende interpretar el score como validacion clinica;
- se quiere usar una respuesta online fresca sin fase separada;
- se intenta versionar datos reales o sensibles por accidente.

## Limites interpretativos

Esta preparacion no valida biologicamente el dataset. Tampoco confirma eficacia
terapeutica, seguridad, accesibilidad real, relevancia clinica ni prioridad de
un blanco. Solo organiza evidencia real para una importacion controlada,
trazable y separada de fuentes no equivalentes.

Un dataset listo para importar no es aun un ranking. Cualquier scoring futuro
debe interpretarse como priorizacion computacional exploratoria y requiere una
fase separada.

## Relacion con otros documentos

- `docs/user_curated_validation_protocol.md`: define que cuenta como
  `user_curated` y como separar fuentes.
- `docs/user_curated_validation_checklist.md`: checklist previo a importacion.
- `docs/user_curated_operational_flow.md`: flujo desde manifest hasta
  prevalidacion/importacion controlada.
- `docs/dataset_import.md`: uso de `import_dataset.py` y la bandera
  `--validate-user-curated-manifest`.
