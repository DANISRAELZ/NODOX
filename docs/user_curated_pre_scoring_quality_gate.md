# User-Curated Pre-Scoring Quality Gate

## Que es el quality gate

El `user_curated pre-scoring quality gate` es una compuerta conservadora previa
a cualquier futura corrida de scoring. Su funcion es ayudar a decidir si un
dataset `user_curated` parece tener procedencia, evidencia, completitud y
limites interpretativos suficientemente claros para pasar a una fase futura
controlada.

Tambien funciona como una primera version de `pre-scoring approval`: una
aprobacion manual previa a scoring, separada del pipeline y de cualquier
calculo cientifico.

No es un modulo de scoring. No interpreta blancos terapeuticos y no declara que
un dataset sea biologicamente o clinicamente valido.

## Por que existe

El flujo `user_curated` permite preparar datos reales aportados o revisados por
el usuario. Antes de cualquier scoring, esos datos deben tener una revision
minima de trazabilidad:

- manifest estructuralmente valido;
- `source_type=user_curated` confirmado;
- procedencia documentada;
- archivos reales identificados;
- ausencia de mezcla demo/proxy/cache como evidencia real;
- faltantes y limitaciones aceptados de forma explicita;
- revision experta pendiente o completada.

El quality gate existe para hacer visible esa decision antes de avanzar.

## Lo que no hace

El quality gate:

- no ejecuta scoring;
- no ejecuta pipeline;
- no ejecuta `run_pipeline.py`;
- no ejecuta Snakemake;
- no ejecuta `import_dataset.py`;
- no calcula `therapeutic_priority_score`;
- no calcula `evidence_confidence_score`;
- no genera rankings;
- no genera outputs cientificos;
- no consulta fuentes online;
- no valida biologica ni clinicamente;
- no sustituye revision experta;
- no sustituye validacion experimental.

## Estados conservadores

La compuerta usa tres estados:

- `not_ready_for_scoring`: hay errores estructurales, placeholders, campos
  criticos vacios o `source_type` distinto de `user_curated`.
- `requires_expert_review`: el manifest valida estructuralmente, pero hay
  evidencia pendiente, procedencia debil, campos no estructurales incompletos o
  senales que requieren decision experta antes de avanzar.
- `conditionally_ready_for_future_controlled_scoring`: el manifest parece
  completo fila por fila para una fase futura controlada, sin placeholders
  evidentes, con `source_type=user_curated` y procedencia documentada.

Incluso el mejor estado es condicional. No significa validacion terapeutica,
biologica o clinica.

## Utilidad operativa

La utilidad pura esta en:

```text
src/nodos_funcionales/user_curated_quality_gate.py
```

Expone:

```python
assess_pre_scoring_readiness(manifest_path)
```

La funcion reutiliza `validate_user_curated_manifest()`, lee el manifest y
devuelve un diccionario con:

- `status`;
- `errors`;
- `warnings`;
- `checklist`.

La utilidad no escribe archivos, no ejecuta comandos externos, no importa
scoring, no consulta internet y no calcula scores cientificos.

## Plantilla de aprobacion

La plantilla editable esta en:

```text
docs/templates/user_curated_pre_scoring_approval_template.md
```

Debe completarse manualmente antes de cualquier futura corrida controlada. La
aprobacion final requiere revision experta y aceptacion explicita de limites.

## Relacion con la GUI

La GUI `user_curated` puede mostrar el estado del quality gate de forma
informativa. Esa vista no ejecuta scoring, no ejecuta pipeline, no muestra
ranking y no genera outputs cientificos.

La GUI tambien puede incorporar ese estado en un resumen final exportable para
revision experta. El resumen se descarga como Markdown local desde Streamlit,
no escribe resultados cientificos y solo muestra el comando manual de
importacion validada cuando el estado conservador aplica.

La GUI sigue siendo opcional. Streamlit no se convierte en dependencia
obligatoria del proyecto.

## Proximo paso seguro

No implementar scoring todavia. El siguiente paso seguro es revisar el quality
gate con usuarios reales, ajustar la plantilla de aprobacion y definir una fase
futura separada para cualquier corrida controlada. Esa fase futura debera tener
pruebas propias, advertencias visibles y separacion estricta entre
`evidence_confidence_score` y `therapeutic_priority_score`.
