# User-curated manual curation transformation

## Proposito

Esta fase implementa una transformacion minima, pura y controlada de
`manual_curation.csv` hacia una salida compatible con
`evidence_quality_template.csv`.

La funcion no importa datasets, no escribe archivos por defecto, no ejecuta
scoring, no ejecuta `run_pipeline.py`, no usa modo online y no genera ranking
terapeutico.

## Por que hace falta

`manual_curation.csv` no se importaba directamente porque no es un dataset
interno aceptado por `import_dataset.py`. La curacion manual contiene contexto,
decision del curador, resumen de evidencia, estado de revision, fuente y notas,
pero no debe transformarse automaticamente en prioridad terapeutica ni en
confianza alta.

## Destino elegido

El primer destino minimo mas seguro es `evidence_quality` porque permite
representar soporte interpretativo por candidato sin mezclarlo con prioridad
terapeutica. `literature_support` se pospone porque una nota local o referencia
pendiente no debe convertirse en DOI, URL verificada ni literatura fuerte sin
una regla adicional de trazabilidad bibliografica.

## Funcion disponible

```python
transform_user_curated_manual_curation_to_evidence_quality(input_path)
```

La funcion vive en:

```text
src/nodos_funcionales/user_curated_transformations.py
```

Devuelve un `DataFrame` con las columnas exactas de
`data_templates/evidence_quality_template.csv`:

```text
protein_id,gene,evidence_quality_score,confidence_ceiling,evidence_source_type,evidence_notes,audit_flags,phase3_notes,database
```

## Campos preservados

La salida preserva directamente:

- `protein_id`;
- `gene`.

La trazabilidad completa se conserva en campos interpretativos:

- `organism`;
- `strain`;
- `curator_name`;
- `curation_date`;
- `curation_decision`;
- `evidence_summary`;
- `evidence_status`;
- `source_database`;
- `reference_or_note`;
- `curator_notes`;
- `source_type=user_curated`.

`evidence_summary` se conserva como explicacion, no como score automatico.
`curator_notes` se preservan. `reference_or_note` requiere trazabilidad antes
de considerarse bibliografia fuerte.

## Valores numericos conservadores

La plantilla exige columnas numericas interpretativas:

- `evidence_quality_score`;
- `confidence_ceiling`.

La transformacion usa valores conservadores:

- `0.20` para `pending_review`, `limited`, evidencia insuficiente o estados no
  fuertes;
- `0.40` para `reviewed` o revision curada generica.

Estos valores son techos interpretativos conservadores. No son
`therapeutic_priority_score`, no son recomendacion clinica y no elevan
automaticamente `evidence_confidence_score`.

## Reglas conservadoras

- `manual_curation.csv` no debe mapearse a `therapeutic_priority_score`.
- `manual_curation.csv` no debe producir recomendacion clinica.
- `manual_curation.csv` no debe elevar confianza automaticamente.
- `pending_review` no equivale a high confidence.
- `include_for_structure_check` no equivale a validacion biologica.
- `local validation note` no equivale a DOI ni literatura verificada.
- `evidence_summary` debe ser explicacion, no score automatico.
- `evidence_quality` debe apoyar interpretacion, no prioridad terapeutica.
- `therapeutic_priority_score` y `evidence_confidence_score` permanecen
  separados.
- Ausencia de evidencia no significa bajo riesgo.
- Evidencia pendiente no significa evidencia negativa.
- `user_curated` no equivale a `demo`, `proxy`, `cache` ni
  `controlled_reference`.
- No se introducen defaults de PAO1, H37Rv ni Corynebacterium.
- El enfoque sigue siendo multi-organismo y theory-first.

## Limites

Esta transformacion no equivale a evidencia clinica, no valida biologicamente
un candidato y no convierte notas locales en bibliografia verificada. La salida
debe revisarse antes de cualquier importacion controlada o corrida real.

## Validacion esperada

La prueba asociada cubre:

- transformacion exitosa con CSV temporal minimo;
- preservacion de `organism`, `strain`, `gene` y `protein_id`;
- preservacion de `curator_name`, `curation_date` y `curation_decision`;
- preservacion de `evidence_summary`, `evidence_status`, `source_database`,
  `reference_or_note` y `curator_notes`;
- `pending_review` sin alta confianza;
- `include_for_structure_check` sin validacion biologica;
- nota local sin DOI ni literatura verificada;
- ausencia de `therapeutic_priority_score`, ranking o recomendacion clinica;
- error claro cuando faltan columnas criticas;
- ausencia de defaults de PAO1, H37Rv o Corynebacterium;
- ausencia de escritura en `user_curated_staging/` o `data_sessions/`;
- ausencia de scoring, pipeline y modo online.

## Estado de cierre

Estado: transformacion minima disponible como funcion pura y testeada. Una fase
posterior puede verificar una importacion controlada de la salida a un
workspace dedicado, sin ejecutar scoring durante la importacion.
