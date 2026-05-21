# User-Curated GUI Phase Closure

## Proposito general

La GUI opcional `user_curated` facilita el onboarding de usuarios nuevos sin
pedirles conocer la arquitectura interna de Nodos Funcionales. Su objetivo es
ayudar a preparar datos reales en staging local, validar el `manifest.csv`,
revisar evidencia y procedencia, y orientar una futura corrida controlada.

La GUI esta disenada como una ayuda visual y operativa. No cambia el pipeline,
no cambia scoring y no convierte datos incompletos en evidencia biologica
suficiente.

## Fases cerradas

### Fase 1: onboarding, staging y validacion de manifest

La primera fase permite crear `user_curated_staging/<project_id>/`, ubicar
`README.md`, `manifest.csv`, `raw_inputs/`, `notes/` y `provenance/`, y validar
el manifest con `validate_user_curated_manifest()`.

### Fase 2: importacion validada asistida como comando manual

La segunda fase muestra el comando manual:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --validate-user-curated-manifest <ruta_manifest.csv>
```

La GUI no ejecuta ese comando. Solo ayuda a recordar que cualquier importacion
validada debe ocurrir despues de una prevalidacion clara del manifest.

### Fase 3: revision visual de calidad/evidencia

La tercera fase agrega una lectura visual y conservadora del manifest. Muestra
campos como `source_type`, `evidence_status`, `evidence_kind`, `provenance`,
`input_file`, `input_schema`, `required_for_scoring` y `notes`, y advierte sobre
placeholders, campos vacios o posible mezcla demo/proxy/cache.

### Fase 4: preparacion para scoring sin ejecutar scoring

La cuarta fase agrega una vista de readiness previa a una futura corrida
controlada. Reutiliza el validador, muestra campos criticos y presenta estados
conservadores como `No listo para scoring`, `Requiere revision experta antes de
scoring` o `Potencialmente listo para una futura corrida controlada`.

### Fase 5: quality gate previo a scoring

La quinta fase agrega una compuerta conservadora que reutiliza el manifest y
devuelve `not_ready_for_scoring`, `requires_expert_review` o
`conditionally_ready_for_future_controlled_scoring`. Sigue siendo una decision
previa a cualquier scoring y no valida biologia ni clinica.

### Fase 6: resumen final exportable para revision experta

La sexta fase agrega un resumen Markdown copiable o descargable desde Streamlit.
Muestra `dataset_id`, archivos detectados, estado del manifest, quality gate,
advertencias principales, decision final y limites interpretativos sin escribir
outputs cientificos del pipeline.

### Fase 7: revision final del flujo completo

La septima fase ordena el recorrido visible en siete pasos: staging local,
revision de archivos locales, validacion de manifest, revision de
evidencia/calidad, quality gate, resumen exportable e importacion validada
asistida como comando manual. El quality gate queda como la compuerta previa a
cualquier scoring futuro y la GUI no muestra botones de importacion ejecutable.

## Limites explicitos

La GUI:

- no ejecuta `import_dataset.py`;
- no ejecuta pipeline;
- no ejecuta `run_pipeline.py`;
- no ejecuta Snakemake;
- no ejecuta scoring;
- no genera rankings;
- no genera outputs cientificos;
- no escribe resumenes en `results/`, `data_processed/` ni `data_sessions/`;
- no calcula `therapeutic_priority_score`;
- no calcula `evidence_confidence_score`;
- no valida biologica ni clinicamente;
- no sustituye revision experta;
- no sustituye validacion experimental.

Incluso si el manifest valida y la vista de readiness es favorable, eso solo
significa que el paquete parece mejor preparado para una fase futura. No
significa que el dataset sea clinicamente suficiente ni que exista validacion
terapeutica.

El resumen final no implica recomendacion terapeutica y no reemplaza revision
experta. Un score alto, en fases futuras, no equivale automaticamente a
confianza alta.

## Archivos principales

- `apps/user_curated_onboarding_app.py`: app Streamlit opcional de onboarding,
  revision visual, importacion asistida como comando manual y readiness.
- `docs/user_curated_gui_onboarding.md`: guia de uso de la GUI.
- `docs/user_friendly_onboarding.md`: guia general para usuarios nuevos.
- `tests/test_user_curated_gui.py`: pruebas textuales de alcance sin importar
  Streamlit.
- `scripts/create_user_curated_staging.py`: scaffold local de staging.
- `src/nodos_funcionales/user_curated_validation.py`: validador reutilizado por
  CLI, scripts y GUI.

## Flujo recomendado

1. Crear staging local.
2. Llenar `README.md`.
3. Llenar `manifest.csv`.
4. Colocar archivos reales en `raw_inputs/`.
5. Documentar procedencia en `provenance/`.
6. Registrar notas en `notes/`.
7. Validar manifest.
8. Revisar calidad/evidencia.
9. Revisar quality gate.
10. Copiar o descargar el resumen final para revision experta.
11. Revisar importacion validada asistida como comando manual.
12. Detenerse antes de cualquier scoring/pipeline.

Durante todo el flujo, `user_curated_staging/` debe permanecer local e ignorado
por Git. No versionar datos reales y no usar `git add .`.

## Pruebas

La GUI queda protegida por pruebas de texto que no importan Streamlit. Esto
mantiene Streamlit como dependencia opcional y evita que la suite falle en
entornos donde la GUI no esta instalada.

Las pruebas verifican que la app:

- reutiliza `validate_user_curated_manifest()`;
- documenta que no ejecuta `import_dataset.py`, `run_pipeline.py`, Snakemake,
  pipeline ni scoring;
- no genera ranking ni outputs cientificos;
- menciona limites biologicos, clinicos, revision experta y validacion
  experimental;
- protege la ausencia de defaults especificos como PAO1, H37Rv,
  Corynebacterium, Pseudomonas aeruginosa y Mycobacterium tuberculosis.

La suite offline `not online` sigue siendo la validacion general recomendada
para confirmar que esta documentacion y las pruebas no ampliaron el alcance.

## Proximo paso seguro

No implementar scoring todavia desde la GUI.

El siguiente paso seguro es usar el resumen final junto con el `quality gate` o
`pre-scoring approval` documentado en
`docs/user_curated_pre_scoring_quality_gate.md` y la plantilla
`docs/templates/user_curated_pre_scoring_approval_template.md`. Esta compuerta
exige aceptacion explicita de limites, revision experta y evidencia suficiente
antes de permitir cualquier corrida controlada.

Cualquier ejecucion futura de scoring debe ser una fase separada, con pruebas,
advertencias visibles y sin mezclar `evidence_confidence_score` con
`therapeutic_priority_score`.
