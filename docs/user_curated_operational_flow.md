# User-Curated Operational Flow

## Proposito

Este documento describe el flujo operativo completo para preparar, revisar,
prevalidar e importar datos `user_curated` sin ejecutar scoring ni pipeline.
Sirve como guia practica entre el protocolo cientifico y el uso de
`import_dataset.py`.

Antes de importar un primer dataset real, usar
`docs/user_curated_real_dataset_readiness.md` para organizar una carpeta local
de staging ignorada por `.gitignore`, revisar procedencia y evitar versionar
datos sensibles. Si se necesita un README local para esa carpeta, copiar
manualmente `docs/templates/user_curated_staging_README_template.md` dentro del
staging ignorado.

El objetivo es asegurar que cada archivo real aportado o revisado por el
usuario tenga estructura minima, procedencia clara y separacion estricta frente
a datos demo, proxy, cache, online o `controlled_reference`.

## Punto de partida

Trabajar siempre desde la raiz del repositorio:

```powershell
cd C:\Users\danis\OneDrive\Escritorio\nodos
```

Antes de empezar, confirmar que la fase es solo de preparacion e importacion
prevalidada:

- no ejecutar `run_pipeline.py`;
- no ejecutar Snakemake;
- no ejecutar scoring;
- no escribir resultados en `results/`, `data_processed/` ni workspaces de
  fases anteriores;
- no usar organismos demo como defaults de datos reales.

## 1. Copiar la plantilla del manifest

Usar como base:

```text
data_templates/user_curated_dataset_manifest_template.csv
```

Copiarla a una ubicacion de trabajo controlada, por ejemplo junto a los datos
reales que se van a revisar:

```powershell
Copy-Item .\data_templates\user_curated_dataset_manifest_template.csv .\path\to\user_data\user_curated_dataset_manifest.csv
```

La copia debe convertirse en el manifest real del dataset. La plantilla contiene
marcadores como `<organism_name>` y `<dataset_id>`; esos valores deben
reemplazarse antes de aceptar el manifest como evidencia real.

## 2. Crear un manifest real `user_curated`

El manifest real debe tener una fila por archivo o capa que se quiera revisar o
importar. Mantener exactamente las columnas de la plantilla:

```text
organism,strain,dataset_id,dataset_version,curator_name,curation_date,source_type,evidence_status,evidence_kind,provenance,input_file,input_schema,required_for_scoring,notes
```

Campos minimos que no deben quedar vacios:

- `organism`: organismo bacteriano evaluado.
- `dataset_id`: capa o coleccion declarada, por ejemplo `essentiality` o
  `virulence`.
- `source_type`: debe ser `user_curated` para evidencia real del usuario.
- `input_file`: archivo de entrada asociado a esa fila.

Campos que deben completarse para trazabilidad operativa:

- `strain`: cepa, aislado, linaje o alcance declarado; si no aplica, escribir
  el alcance usado.
- `dataset_version`: version local, fecha de export o revision.
- `curator_name`: persona o equipo responsable de la revision.
- `curation_date`: fecha de curacion en formato claro, preferentemente
  `YYYY-MM-DD`.
- `evidence_status`: por ejemplo `reviewed`, `pending_review` o
  `incomplete`.
- `evidence_kind`: tipo de evidencia, por ejemplo `experimental`,
  `literature`, `local_export`, `reviewed_annotation` o `mixed`.
- `provenance`: fuente, herramienta, catalogo, cita o descripcion del export.
- `input_schema`: plantilla o esquema esperado, por ejemplo
  `data_templates/essentiality_template.csv`.
- `required_for_scoring`: `true` si la capa es necesaria para avanzar a scoring
  en una fase posterior; `false` si es auxiliar u opcional.
- `notes`: limites, faltantes, inferencias, proxies marcados o decisiones de
  curacion.

## 3. Separar `user_curated` de otras fuentes

Usar `source_type=user_curated` solo cuando la evidencia fue aportada o revisada
por el usuario para el organismo y alcance declarados. No usarlo para datos que
solo prueban el software o para resultados heredados sin revision.

Separacion requerida:

| Categoria | Significado operativo | Uso en este flujo |
| --- | --- | --- |
| `user_curated` | Evidencia real, especifica del organismo, aportada o revisada por el usuario. | Permitida como fuente principal. |
| `controlled_reference` | Snapshot o referencia congelada para comparar contratos o reproducibilidad. | No debe presentarse como evidencia real del organismo nuevo. |
| demo | Datos pequenos de ejemplo, incluyendo organismos usados para demostrar el sistema. | No usar como evidencia real. |
| proxy | Valor aproximado, fallback o inferencia marcada. | Solo puede aparecer como limitacion declarada. |
| cache | Respuesta o capa reutilizada de una ejecucion previa. | No sustituye evidencia curada nueva. |
| online | Respuesta fresca de proveedor externo. | Fuera de este flujo; requiere fase separada. |

El manifest no debe contener defaults de organismos de ejemplo como PAO1,
H37Rv, `Pseudomonas aeruginosa`, `Mycobacterium tuberculosis` o
`Corynebacterium`. Si aparecen como residuos de plantilla, demo o referencia,
corregir el manifest antes de avanzar.

## 4. Revisar archivos antes de prevalidar

Antes de ejecutar herramientas, confirmar manualmente:

- cada `input_file` existe;
- cada archivo pertenece al organismo y alcance declarados;
- los identificadores principales, como `protein_id` o `gene`, no son
  marcadores de plantilla;
- las capas obligatorias previstas tienen procedencia clara;
- cualquier faltante, inferencia o proxy esta marcado en columnas, notas o
  manifest.

Esta revision manual es parte del flujo. La prevalidacion automatica solo
comprueba estructura y procedencia minima del manifest.

## 5. Prevalidar con CLI Python

Ejecutar la prevalidacion estructural del manifest:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py <ruta_manifest.csv>
```

Ejemplo:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py .\path\to\user_data\user_curated_dataset_manifest.csv
```

Si el manifest es valido para revision/importacion, el comando devuelve codigo
`0` y muestra mensajes `[OK]`. Si hay errores, devuelve un codigo distinto de
`0`, imprime la lista de problemas y el manifest debe corregirse antes de
avanzar.

## 6. Prevalidar con wrapper PowerShell

En Windows tambien puede usarse el wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 <ruta_manifest.csv>
```

Ejemplo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 .\path\to\user_data\user_curated_dataset_manifest.csv
```

El `Bypass` aplica solo a ese comando. El wrapper resuelve Python, llama al
script de prevalidacion y conserva el mismo significado de codigos de salida:
`0` si no hay errores estructurales y distinto de `0` si el manifest debe
corregirse.

## 7. Corregir errores antes de importar

Si la prevalidacion falla, detener el flujo y corregir el manifest. Errores
frecuentes:

- columnas distintas a la plantilla;
- `source_type` diferente de `user_curated`;
- `organism`, `dataset_id` o `input_file` vacios;
- defaults de organismos demo o referencia;
- manifest sin filas de dataset;
- ruta equivocada o archivo inexistente.

No continuar a importacion mientras el manifest conserve errores conocidos o
exista incertidumbre sobre la procedencia.

## 8. Importar con prevalidacion opt-in

Cuando el manifest ya paso la revision automatica y manual, usar
`import_dataset.py` con la bandera explicita:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --workspace <workspace_destino> --dataset <dataset> --input <archivo_de_entrada.csv> --validate-user-curated-manifest <ruta_manifest.csv>
```

Ejemplo generico:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace data_sessions\user_curated_workspace --dataset essentiality --input .\path\to\user_data\essentiality.csv --validate-user-curated-manifest .\path\to\user_data\user_curated_dataset_manifest.csv
```

La bandera `--validate-user-curated-manifest` hace que el importador revise el
manifest antes de copiar o normalizar datos. Si hay errores, la importacion se
detiene.

Este paso sigue siendo una importacion prevalidada, no una corrida del pipeline.
Despues de importar las capas necesarias, detenerse y revisar lo importado antes
de decidir una fase posterior.

## 9. Detenerse antes de scoring o pipeline

El cierre de este flujo ocurre antes de cualquier priorizacion. No ejecutar:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py ...
```

Tampoco ejecutar comandos de Snakemake ni scripts que escriban reportes finales.
La siguiente decision debe ser una revision humana: verificar manifest, archivos
de entrada, importacion realizada y limites de evidencia antes de pasar a una
fase de pipeline.

## Limites de esta validacion

Esta validacion:

- no ejecuta scoring;
- no ejecuta pipeline;
- no valida biologicamente el dataset;
- no convierte automaticamente evidencia debil en evidencia alta;
- no aumenta `evidence_confidence_score` por si sola;
- no implica que un blanco terapeutico sea clinicamente valido;
- solo valida estructura, procedencia minima y separacion de fuentes.

Pasar la prevalidacion significa que el manifest cumple un contrato minimo para
revision o importacion controlada. No significa que la evidencia sea suficiente
para interpretar un ranking terapeutico.

## Criterios para avanzar

Avanzar a importacion prevalidada solo si:

- el manifest no tiene errores;
- los archivos de entrada estan presentes;
- la procedencia es clara;
- cada fila real usa `source_type=user_curated`;
- no hay datos demo, proxy o cache usados como si fueran datos reales;
- `controlled_reference` no se mezcla con evidencia principal del organismo;
- la revision manual fue aceptada antes de importar.

Avanzar a una fase posterior de pipeline solo requiere una decision separada,
despues de revisar que las capas importadas sean correctas y suficientes.

## Criterios para detener

Detener el flujo si ocurre cualquiera de estos casos:

- manifest incompleto;
- `source_type` incorrecto;
- campos obligatorios vacios;
- mezcla con demo, proxy o cache como evidencia principal;
- defaults de organismos de ejemplo;
- errores de procedencia;
- falta de archivos de entrada;
- incertidumbre sobre la evidencia;
- uso accidental de `controlled_reference` como si fuera `user_curated`;
- dependencia de una consulta online fresca para interpretar el archivo.

Cuando el flujo se detiene, corregir manifest, archivos o notas de procedencia
antes de volver a prevalidar.

## Cierre esperado

El flujo operativo queda completo cuando:

- existe un manifest real basado en la plantilla;
- el manifest fue revisado manualmente;
- la CLI Python o el wrapper PowerShell pasan sin errores;
- la importacion, si se ejecuta, usa
  `--validate-user-curated-manifest <ruta_manifest.csv>`;
- el trabajo se detiene antes de scoring, pipeline y Snakemake;
- los limites de evidencia quedan documentados para la siguiente revision.
