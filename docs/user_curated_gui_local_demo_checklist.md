# User-Curated GUI Local Demo Checklist

## Proposito

Esta checklist prepara una demo local controlada de la GUI `user_curated`.
Sirve para recorrer visualmente el flujo completo sin ejecutar scoring, sin
ejecutar pipeline, sin generar rankings y sin usar datos reales.

La demo no es una validacion biologica, clinica ni terapeutica. Tampoco convierte
una plantilla en evidencia `user_curated` real.

## Dataset de prueba

Usar el manifest template incluido:

```text
data_templates/user_curated_dataset_manifest_template.csv
```

Ese archivo conserva placeholders de forma intencional. Por eso la validacion,
las advertencias y el quality gate deben mantenerse conservadores durante la
demo. No mezclarlo con demo, proxy, cache, `controlled_reference`, online ni
datos reales.

## Abrir la GUI

Desde la raiz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps\user_curated_onboarding_app.py
```

Si Streamlit no esta instalado en el entorno local, seguir la guia de
`docs/user_curated_gui_onboarding.md` antes de la demo.

## Recorrido visual

Revisar la secuencia final:

1. staging local del dataset;
2. revision de archivos locales;
3. validacion de `manifest.csv`;
4. revision de evidencia/calidad;
5. quality gate previo a scoring;
6. resumen exportable para revision experta;
7. importacion validada asistida como comando manual.

Para las entradas de manifest en validacion, revision visual, quality gate y
resumen final, usar:

```text
data_templates/user_curated_dataset_manifest_template.csv
```

## Checklist de observacion

- [ ] La GUI abre sin errores visibles.
- [ ] La secuencia visible conserva los siete pasos del flujo final.
- [ ] Se identifica el `dataset_id` del manifest de prueba o su placeholder.
- [ ] Se detectan los archivos esperados o se marca claramente que no se
      detectan cuando el template conserva rutas placeholder.
- [ ] `manifest.csv` se valida de forma conservadora y muestra errores si el
      template conserva placeholders.
- [ ] Se muestran advertencias de evidencia o `provenance` cuando aplica.
- [ ] El quality gate muestra una decision conservadora.
- [ ] El resumen experto es visible y exportable como Markdown local.
- [ ] La importacion aparece solo como comando manual.
- [ ] No hay boton ni accion que ejecute scoring.
- [ ] No hay boton ni accion que ejecute pipeline.
- [ ] No se generan rankings.
- [ ] No se escriben archivos en `results/`, `data_processed/`,
      `data_sessions/` ni snapshots.
- [ ] Se mantiene separacion explicita entre `user_curated`, demo, proxy,
      cache, `controlled_reference` y online.

## Que NO debe hacer la GUI

Durante la demo, la GUI:

- no ejecuta scoring;
- no ejecuta pipeline;
- no llama `run_pipeline.py`;
- no ejecuta Snakemake;
- no genera rankings;
- no escribe outputs cientificos;
- no convierte un quality gate favorable en recomendacion terapeutica;
- no sustituye revision experta.

## Cerrar la demo

1. Cerrar la pestana local de Streamlit si ya no se necesita.
2. Volver a la terminal que ejecuta Streamlit.
3. Presionar `Ctrl+C`.
4. Revisar `git status --short` para confirmar que no quedaron datos reales ni
   outputs cientificos en el arbol.

## Documentar observaciones

Registrar fecha, revisor, sistema local, manifest de prueba usado, pasos
revisados, advertencias vistas y cualquier texto ambiguo detectado. Guardar las
observaciones como nota de revision del equipo, no como output cientifico del
pipeline.
