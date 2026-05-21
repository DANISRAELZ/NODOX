# User-Curated GUI Onboarding

## Objetivo

Esta guia describe la primera interfaz grafica opcional para preparar datos
`user_curated` en Nodos Funcionales. La GUI esta pensada para usuarios nuevos
que quieren crear staging local y prevalidar un `manifest.csv` sin conocer la
arquitectura interna del proyecto.

El cierre tecnico y operativo de las fases GUI 1-6 esta resumido en
`docs/user_curated_gui_phase_closure.md`.

Esta fase incluye `user-curated GUI phase 4: scoring readiness view`. Agrega una
vista de preparacion para scoring que ayuda a revisar si un manifest parece
preparado para una futura corrida controlada, sin ejecutar scoring, pipeline ni
Snakemake. La app sigue mostrando la importacion validada asistida con
`import_dataset.py --validate-user-curated-manifest`, sin ejecutar el comando
desde la GUI y sin ampliar el alcance hacia rankings, outputs cientificos ni
consulta online.

Tambien puede mostrar un `quality gate` previo a scoring como estado
informativo. Ese quality gate reutiliza la revision conservadora documentada en
`docs/user_curated_pre_scoring_quality_gate.md`; no ejecuta scoring, no ejecuta
pipeline, no genera ranking y requiere revision experta y validacion
experimental futura.

La fase 6 agrega un `Resumen final exportable para revision experta`. La GUI
genera Markdown local en memoria para copiarlo o descargarlo desde Streamlit.
Ese resumen junta `dataset_id`, archivos detectados, estado de `manifest.csv`,
resultado del quality gate, advertencias principales y decision final sin crear
outputs cientificos.

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
- mostrar un mensaje de exito cuando el manifest cumple el contrato minimo;
- mostrar una checklist visual de preparacion;
- leer visualmente un `manifest.csv` seleccionado;
- mostrar campos principales como `organism`, `strain`, `dataset_id`,
  `dataset_version`, `source_type`, `evidence_status`, `evidence_kind`,
  `provenance`, `input_file`, `input_schema`, `required_for_scoring` y `notes`;
- advertir sobre placeholders, campos criticos vacios, `source_type` distinto
  de `user_curated`, evidencia pendiente, procedencia debil y posible mezcla
  demo/proxy/cache;
- mostrar una checklist visual de revision de evidencia;
- mostrar una seccion de `Preparacion para scoring (sin ejecutar scoring)`;
- mostrar si el manifest valida estructuralmente;
- mostrar un estado conservador: `No listo para scoring`,
  `Requiere revision experta antes de scoring` o
  `Potencialmente listo para una futura corrida controlada`;
- mostrar una seccion informativa de `Quality gate previo a scoring`;
- mostrar estados conservadores como `not_ready_for_scoring`,
  `requires_expert_review` y
  `conditionally_ready_for_future_controlled_scoring`;
- mostrar un `Resumen final exportable para revision experta`;
- generar Markdown copiable o descargable desde Streamlit sin escribir en
  `results/`, `data_processed/` ni `data_sessions/`;
- incluir en el resumen archivos detectados, estado de manifest, quality gate,
  advertencias, decision final y limites interpretativos;
- mostrar un comando manual de importacion validada en el resumen solo cuando
  el estado conservador aplica;
- mostrar una seccion de `Importacion validada asistida`;
- mostrar comandos manuales para pasos posteriores sin ejecutarlos;
- dejar visible que la GUI se detiene antes de pipeline, scoring, rankings y
  outputs cientificos.

## Ayuda contextual visible

La interfaz incluye secciones explicitas de orientacion:

- `Que hace esta GUI`: resume que solo crea staging local y prevalida manifest.
- `Que NO hace esta GUI`: recuerda que no ejecuta pipeline, no ejecuta scoring,
  no genera outputs cientificos ni rankings, no valida biologicamente, no valida
  clinicamente y no sustituye revision experta.
- Revision de archivos locales: indica que los datos reales van solo en
  `raw_inputs/`, que la procedencia se documenta en `provenance/` y que las
  decisiones, limites o faltantes se revisan en `notes/`.
- Checklist visual: recuerda revisar `README.md`, completar `manifest.csv`,
  usar `source_type=user_curated`, evitar mezcla demo/proxy/cache, revisar
  `git status --short` y detenerse antes de pipeline/scoring.
- `Revision visual de calidad/evidencia del dataset`: muestra el contenido
  principal del manifest, senala placeholders o campos vacios y da una
  conclusion conservadora.
- `Preparacion para scoring (sin ejecutar scoring)`: revisa campos clave como
  `source_type`, `evidence_status`, `provenance`, `input_file` y
  `required_for_scoring`; muestra readiness conservador antes de una fase futura.
- `Quality gate previo a scoring`: muestra una evaluacion conservadora y
  editable por revision experta antes de cualquier scoring futuro.
- `Resumen final exportable para revision experta`: genera Markdown copiable o
  descargable con el estado del paquete antes de cualquier scoring.
- `Importacion validada asistida`: muestra una checklist previa a la importacion
  manual y el comando sugerido con `--validate-user-curated-manifest`, pero no
  lo ejecuta.
- `La GUI se detiene aqui`: recuerda que no hay pipeline, scoring, ranking,
  outputs cientificos, validacion clinica ni validacion biologica.

Cuando se crea staging, la GUI muestra las rutas esperadas y advierte que
`user_curated_staging/` debe permanecer ignorado por Git.

## Limites

Esta GUI no ejecuta pipeline, no ejecuta scoring, no ejecuta Snakemake, no llama
a `import_dataset.py`, no genera rankings y no genera outputs cientificos.
Tampoco valida biologicamente el dataset: solo prevalidacion estructural y de
procedencia minima del manifest.

La revision visual de evidencia es orientativa: no calcula `confidence_score`,
no calcula `therapeutic_priority_score`, no interpreta blancos terapeuticos y no
declara que el dataset sea biologicamente o clinicamente valido. Sirve para
revisar procedencia y completitud antes de avanzar.

La vista de preparacion para scoring tambien es orientativa. No calcula
`therapeutic_priority_score`, no calcula `evidence_confidence_score`, no genera
ranking y no ejecuta scoring ni pipeline. Un estado favorable solo significa
que el manifest parece potencialmente listo para una futura corrida controlada;
no significa validacion biologica, suficiencia clinica ni conclusion
terapeutica.

El quality gate previo a scoring tambien es orientativo y conservador. No
calcula `therapeutic_priority_score`, no calcula `evidence_confidence_score`,
no ejecuta scoring, no ejecuta pipeline, no genera ranking y no genera outputs
cientificos. Sirve para ordenar una decision humana antes de una fase futura;
no reemplaza revision experta ni validacion experimental.

El resumen final exportable no es un reporte cientifico. No es validacion
biologica, no es validacion clinica, no implica recomendacion terapeutica y no
sustituye revision experta. Un score alto, en fases futuras, no equivale
automaticamente a confianza alta. El resumen mantiene `user_curated` separado
de demo, proxy, cache, `controlled_reference` y online.

La GUI no forma parte obligatoria del pipeline. Streamlit sigue siendo una
dependencia opcional y la app puede usarse solo como ayuda visual de preparacion
local.

La GUI no sustituye revision experta, curacion biologica ni validacion
experimental. Un manifest valido solo indica que cumple el contrato minimo para
revision o una fase posterior de importacion controlada.

Si el manifest valida, eso no implica suficiencia cientifica. Si el manifest no
valida, los errores deben corregirse antes de importar en una fase posterior.

La GUI puede mostrar este comando como siguiente paso manual, pero no lo ejecuta:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --validate-user-curated-manifest <ruta_manifest.csv>
```

La importacion validada, si el usuario la realiza manualmente fuera de la GUI,
no equivale a scoring, no genera ranking terapeutico y no produce conclusiones
terapeuticas. Incluso despues de importar, el dataset no debe interpretarse como
validacion terapeutica, biologica o clinica.

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
8. Revisar la seccion `Revision visual de calidad/evidencia del dataset`.
9. Revisar la seccion `Preparacion para scoring (sin ejecutar scoring)`.
10. Revisar la seccion `Quality gate previo a scoring`.
11. Generar o descargar el `Resumen final exportable para revision experta`.
12. Revisar la seccion `Importacion validada asistida`.
13. Si corresponde, copiar el comando manual fuera de la GUI y adaptarlo con
   workspace, dataset e input reales.
14. Detenerse antes de pipeline, scoring, ranking o interpretacion terapeutica.

La importacion con `import_dataset.py` queda para una fase posterior y debe
seguir usando validacion explicita del manifest. La GUI fase 2 solo muestra el
comando manual y no ejecuta `import_dataset.py`. Cualquier avance a scoring debe
ser una fase futura controlada despues de un quality gate y revision experta.
