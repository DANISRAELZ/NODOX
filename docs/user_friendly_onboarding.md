# User-Friendly Onboarding

## Proposito

Esta guia esta escrita para una persona que quiere empezar a usar Nodos
Funcionales con sus propios archivos, pero todavia no necesita entender la
arquitectura interna del proyecto.

El objetivo de esta fase es preparar un primer paquete `user_curated` de forma
ordenada, local y revisable. Esta guia no cambia el scoring, no ejecuta el
pipeline y no agrega datos reales al repositorio.

## Que es Nodos Funcionales

Nodos Funcionales es un proyecto bioinformatico para priorizar posibles blancos
terapeuticos bacterianos de forma explicable. El sistema combina capas de
evidencia, como esencialidad, virulencia, localizacion, homologos humanos,
contexto clinico o redes funcionales, para producir rankings interpretables.

La idea central no es solo decir "este gen parece importante", sino mostrar de
donde viene la evidencia, que tan confiable es y que limitaciones tiene.

## Que NO es

Nodos Funcionales no es una herramienta de diagnostico clinico. Tampoco confirma
que una terapia funcione, no reemplaza una revision experta y no convierte un
archivo incompleto en evidencia biologica fuerte.

En esta fase, tampoco es un dashboard, una API, una aplicacion grafica ni un
sistema automatico de descubrimiento con datos online obligatorios.

## Que significa `user_curated`

`user_curated` significa que los datos fueron aportados, revisados o aceptados
por el usuario para un organismo y un alcance concretos. Por ejemplo, una tabla
de esencialidad revisada para una cepa, un export local revisado o una curacion
manual de literatura.

No debe usarse `user_curated` para datos demo, cache, proxies no marcados,
snapshots de referencia o archivos copiados sin revisar. Si una evidencia es
incompleta, inferida o aproximada, debe quedar indicada en el manifest, en las
notas o en la procedencia.

## Que es un manifest

El manifest es una tabla CSV que describe los archivos que el usuario quiere
preparar o importar. Funciona como una portada trazable del dataset.

Cada fila del manifest debe explicar, al menos:

- que organismo y cepa o alcance se esta usando;
- que capa o dataset representa el archivo;
- quien lo curo o reviso;
- de donde salio la evidencia;
- que archivo real se debe usar;
- si el archivo es requerido para una fase posterior de scoring;
- que faltantes, dudas o limites tiene.

El manifest no contiene necesariamente todos los datos biologicos. Su funcion
principal es documentar y controlar la entrada.

## Que es staging local

El staging local es una carpeta de trabajo ignorada por Git donde se preparan
datos reales antes de importarlos. La ruta recomendada es:

```text
user_curated_staging/<project_id>/
```

Dentro de esa carpeta se organizan:

- `README.md`: resumen local del paquete de entrada;
- `manifest.csv`: manifest del dataset;
- `raw_inputs/`: archivos reales;
- `provenance/`: referencias, versiones, citas o descripcion de origen;
- `notes/`: decisiones de curacion, faltantes y limites.

Esta carpeta sirve para trabajar con cuidado antes de tocar un workspace de
importacion. No es una salida del pipeline.

## Por que no subir datos reales al repo

Los datos reales pueden ser privados, sensibles, incompletos, no liberados o
dificiles de redistribuir. Por eso deben quedarse en carpetas locales ignoradas
por Git mientras se revisan.

Regla practica: no versionar datos reales.

No usar `git add .` durante esta preparacion. Antes y despues de copiar archivos
reales, revisar:

```powershell
git status --short
```

Si Git muestra archivos reales dentro de la lista de cambios, detenerse y mover
esos archivos a una ruta ignorada antes de continuar.

## Prevalidar, importar, correr pipeline y hacer scoring

Estos pasos no significan lo mismo:

| Paso | Que hace | Que no hace |
| --- | --- | --- |
| Prevalidar | Revisa que el manifest tenga estructura minima, campos obligatorios y rutas coherentes. | No valida biologia, no importa datos, no corre pipeline y no calcula scores. |
| Importar | Copia o normaliza un archivo del usuario hacia un workspace usando `import_dataset.py`. | No confirma que el dataset sea cientificamente suficiente. |
| Correr pipeline | Ejecuta el flujo de resolucion, integracion, scoring y reportes segun la configuracion. | No debe hacerse en esta fase de onboarding. |
| Hacer scoring | Calcula prioridades y scores interpretables desde las capas disponibles. | No equivale a validacion clinica o experimental. |

En esta fase se llega, como maximo, a prevalidar el manifest e importar con una
validacion explicita. Despues hay que detenerse antes de scoring o pipeline.

## Que significa que un archivo "valide"

Cuando el validador dice que un manifest valida, significa que cumple un
contrato tecnico minimo: tiene las columnas esperadas, no conserva placeholders
criticos, usa `source_type=user_curated` cuando corresponde y apunta a archivos
de entrada declarados.

Eso no significa que el archivo sea biologicamente correcto, suficiente,
completo o clinicamente util. Significa que puede pasar a revision o importacion
controlada sin errores estructurales evidentes.

## Primer uso recomendado

1. Crear staging:

```powershell
.\.venv\Scripts\python.exe scripts\create_user_curated_staging.py <project_id>
```

2. Revisar la carpeta creada:

```powershell
Get-ChildItem user_curated_staging\<project_id>
```

3. Llenar el README local:

```text
user_curated_staging/<project_id>/README.md
```

4. Llenar el manifest:

```text
user_curated_staging/<project_id>/manifest.csv
```

5. Colocar archivos reales en:

```text
user_curated_staging/<project_id>/raw_inputs/
```

6. Documentar procedencia en:

```text
user_curated_staging/<project_id>/provenance/
```

7. Validar manifest:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py user_curated_staging\<project_id>\manifest.csv
```

En Windows tambien puede usarse el wrapper PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 user_curated_staging\<project_id>\manifest.csv
```

8. Importar con validacion explicita:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --validate-user-curated-manifest user_curated_staging\<project_id>\manifest.csv
```

En una importacion real normalmente tambien se indicaran `--organism`,
`--strain`, `--workspace`, `--dataset` e `--input`, segun el archivo que se vaya
a importar.

9. Detenerse antes de scoring o pipeline.

No ejecutar `run_pipeline.py`, Snakemake ni scripts de scoring durante este
onboarding. En otras palabras: no ejecutar pipeline y no ejecutar scoring en
esta fase.

## GUI opcional

Existe una primera GUI opcional de onboarding para ayudar a crear staging local
y prevalidar el manifest. Esta GUI usa Streamlit si esta instalado localmente,
pero Streamlit no es una dependencia obligatoria del proyecto en esta fase.

La guia de uso esta en `docs/user_curated_gui_onboarding.md`. La GUI muestra
una checklist visual, rutas esperadas del staging y mensajes de validacion mas
claros. En fase 2 tambien muestra una seccion de importacion validada asistida
con el comando manual de `import_dataset.py --validate-user-curated-manifest`,
pero no lo ejecuta desde la GUI. No ejecuta pipeline ni scoring, no genera
rankings ni outputs cientificos y no sustituye revision experta.

## Que hacer si falta un archivo

Si el manifest menciona un archivo en `input_file` y ese archivo no existe,
detenerse. No inventar una tabla vacia para pasar el validador.

Opciones recomendadas:

- colocar el archivo real correcto dentro de `raw_inputs/`;
- corregir la ruta en `input_file`;
- quitar temporalmente esa fila si la capa no esta lista;
- marcar el faltante en `notes` si la ausencia es una limitacion conocida.

Despues de corregir, ejecutar de nuevo la validacion del manifest.

## Que hacer si el manifest no valida

Si el manifest no valida, no importar. Leer los errores impresos por el
validador, corregir el CSV y repetir la validacion.

Los problemas mas comunes son columnas modificadas, placeholders sin reemplazar,
`source_type` incorrecto, campos obligatorios vacios o archivos declarados que
no existen.

## Errores frecuentes y solución

| Error frecuente | Solucion recomendada |
| --- | --- |
| PowerShell bloquea scripts no firmados. | Ejecutar el wrapper con `powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 ...`. El bypass aplica solo a ese comando. |
| El manifest conserva placeholders como `<organism_name>` o `<dataset_id>`. | Reemplazar todos los placeholders por valores reales o por una declaracion explicita de alcance. |
| Falta `source_type=user_curated`. | Completar `source_type` exactamente como `user_curated` para evidencia real revisada por el usuario. |
| El archivo listado en `input_file` no existe. | Mover el archivo real a `raw_inputs/` o corregir la ruta del manifest. |
| Git muestra archivos reales. | Detenerse, moverlos a una carpeta ignorada y confirmar con `git status --short`. No usar `git add .`. |
| Se intenta correr scoring antes de revisar procedencia. | Detenerse. Revisar manifest, README local, notas y procedencia antes de decidir una fase posterior. |
| Se mezclan datos demo, cache o proxy como si fueran reales. | Separar fuentes o marcar claramente la limitacion. No declararlos como `user_curated` sin revision. |
| El importador se detiene al validar. | Corregir primero el manifest. La bandera `--validate-user-curated-manifest` esta protegiendo la importacion. |

## Límites de interpretación

Prevalidar no es validacion biologica. Solo confirma que el manifest cumple
reglas tecnicas minimas.

Importar no significa que el dataset sea cientificamente suficiente. Solo mueve
o normaliza datos hacia un workspace con una revision previa del manifest.

Un score alto no equivale a validacion clinica. El sistema prioriza blancos
candidatos, no confirma terapias.

Los resultados futuros deben interpretarse como priorizacion computacional
exploratoria. Siempre se requiere revision experta y validacion experimental;
cuando aplique, tambien se requiere evaluacion clinica independiente.

## Siguiente paso logico

Despues de este onboarding, el siguiente paso recomendado es revisar
manualmente el paquete de staging con una checklist de procedencia: confirmar
que cada archivo pertenece al organismo declarado, que las fuentes son
trazables, que los faltantes estan marcados y que el equipo acepta avanzar a una
fase separada de importacion o pipeline.
