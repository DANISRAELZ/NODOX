# User-Curated GUI Onboarding

## Objetivo

Esta guia describe la primera interfaz grafica opcional para preparar datos
`user_curated` en Nodos Funcionales. La GUI esta pensada para usuarios nuevos
que quieren crear staging local y prevalidar un `manifest.csv` sin conocer la
arquitectura interna del proyecto.

## Alcance

La app permite:

- ingresar un `project_id`;
- crear `user_curated_staging/<project_id>/` usando la logica existente de
  `scripts/create_user_curated_staging.py`;
- mostrar la ruta creada;
- mostrar las rutas esperadas: `README.md`, `manifest.csv`, `raw_inputs/`,
  `notes/` y `provenance/`;
- indicar la ruta de un `manifest.csv` existente;
- validar el manifest con `validate_user_curated_manifest()`;
- mostrar errores de validacion de forma legible;
- mostrar un mensaje de exito cuando el manifest cumple el contrato minimo.

## Limites

Esta GUI no ejecuta pipeline, no ejecuta scoring, no ejecuta Snakemake, no llama
a `import_dataset.py`, no genera rankings y no genera outputs cientificos.
Tampoco valida biologicamente el dataset: solo prevalidacion estructural y de
procedencia minima del manifest.

La GUI no sustituye revision experta, curacion biologica ni validacion
experimental. Un manifest valido solo indica que cumple el contrato minimo para
revision o una fase posterior de importacion controlada.

No subir ni versionar datos reales. Los archivos reales deben permanecer en
rutas locales ignoradas, como `user_curated_staging/<project_id>/raw_inputs/`.
Antes y despues de copiar archivos reales, revisar:

```powershell
git status --short
```

## Como ejecutarla

Desde la raiz del repositorio:

```powershell
streamlit run apps/user_curated_onboarding_app.py
```

Streamlit es una dependencia opcional para esta primera GUI. Si no esta
instalado en el entorno local, instalarlo manualmente antes de ejecutar la app:

```powershell
pip install streamlit
```

Tambien puede instalarse desde el Python del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install streamlit
```

Y ejecutarse desde el mismo entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps\user_curated_onboarding_app.py
```

No se agrega Streamlit a las dependencias globales del proyecto en esta fase.

## Validacion manual local

La GUI opcional fue probada localmente en Windows con el entorno `.venv`.
Streamlit no estaba instalado inicialmente, por lo que se instalo de forma
local y manual:

```powershell
.\.venv\Scripts\python.exe -m pip install streamlit
```

Despues se ejecuto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps\user_curated_onboarding_app.py
```

La interfaz abrio correctamente para revision visual. Esta validacion manual no
ejecuto pipeline, no ejecuto scoring, no genero rankings y no genero outputs
cientificos. Streamlit sigue siendo opcional y no se agrega como dependencia
obligatoria del proyecto.

## Flujo recomendado

1. Abrir la app con Streamlit.
2. Ingresar un `project_id` multiorganismo y crear staging local.
3. Completar el `README.md` local.
4. Completar `manifest.csv` y reemplazar placeholders.
5. Colocar archivos reales solo en `raw_inputs/`.
6. Documentar procedencia en `provenance/`.
7. Validar el manifest desde la GUI.
8. Detenerse antes de importacion, pipeline y scoring.

La importacion con `import_dataset.py` queda para una fase posterior y debe
seguir usando validacion explicita del manifest.
