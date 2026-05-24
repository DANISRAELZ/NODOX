# User-curated manual curation mapping specification

## Proposito

Esta fase define como debe tratarse `manual_curation.csv` como evidencia
curada por usuario, sin implementar transformacion todavia y sin importarlo
directamente. La evidencia manual debe mapearse primero a evidencia
interpretativa, preservando trazabilidad, curador, resumen de evidencia, estado
de evidencia, fuente y notas.

Entrada local conceptual:

```text
user_curated_staging/minimal_user_curated_validation_01/raw_inputs/manual_curation.csv
```

Columnas observadas:

- `organism`;
- `strain`;
- `protein_id`;
- `gene`;
- `curator_name`;
- `curation_date`;
- `curation_decision`;
- `evidence_summary`;
- `evidence_status`;
- `source_database`;
- `reference_or_note`;
- `curator_notes`.

## Alcance de esta fase

Esta fase solo crea una especificacion documental y prueba de contrato:

- no implementa transformacion;
- no ejecuta importaciones nuevas;
- no ejecuta scoring;
- no ejecuta `run_pipeline.py`;
- no ejecuta modo online;
- no genera ranking terapeutico;
- no modifica `src/nodos_funcionales/scoring.py`;
- no modifica `import_dataset.py`;
- no modifica `run_pipeline.py`;
- no modifica snapshots;
- no modifica `results/`;
- no modifica `data_processed/`;
- no modifica `data_sessions/`;
- no modifica `config/taxon_resolution_cache.json`;
- no toca ni versiona `user_curated_staging/`.

## Principio central

`manual_curation.csv` no es dataset interno aceptado directamente por
`import_dataset.py`. No debe forzarse su importacion solo porque exista un CSV.
Tampoco debe convertirse automaticamente en `therapeutic_priority_score`,
`evidence_confidence_score`, confianza alta ni recomendacion clinica.

La curacion manual puede orientar interpretacion, pero no equivale por si sola
a evidencia experimental, evidencia bibliografica verificada ni validacion
biologica.

## Tabla de decision

| Destino conceptual | Uso potencial | Riesgo | Regla | Estado |
| --- | --- | --- | --- | --- |
| `evidence_quality` | Representar calidad/confianza de evidencia por candidato; registrar si la evidencia esta pendiente, revisada, limitada o insuficiente; apoyar interpretacion de confidence, no priority. | Convertir `manual_curation.csv` en `evidence_confidence_score` alto de forma automatica. | `evidence_status=pending_review` o `limited` no debe traducirse a alta confianza; `curation_decision=include_for_structure_check` no significa evidencia experimental; `evidence_summary` debe conservarse como explicacion, no como score automatico. | `requires_controlled_transformation` |
| `literature_support` | Registrar referencia, nota, DOI, URL o evidencia bibliografica; preservar `reference_or_note`; mantener evidencia bibliografica fuera del scoring si el proyecto asi lo define. | Tratar una nota local como literatura validada; confundir `reference_or_note` con DOI verificado. | Una nota local debe marcarse como `local_note` o `pending_reference`; una referencia debe tener identificador trazable antes de considerarse bibliografia fuerte. | `requires_controlled_transformation` |
| `therapeutic_priority_score` | No permitido. | Convertir curacion manual en prioridad terapeutica directa. | `manual_curation.csv` nunca debe convertirse directamente en prioridad terapeutica. | `forbidden_direct_mapping` |
| `clinical recommendation` | No permitido. | Convertir curacion manual en recomendacion clinica. | `manual_curation.csv` nunca debe interpretarse como recomendacion clinica. | `forbidden_direct_mapping` |

## Reglas obligatorias

- `manual_curation.csv` no es dataset interno aceptado directamente por
  `import_dataset.py`.
- No debe forzarse su importacion solo porque exista un CSV.
- No debe mapearse automaticamente a score.
- No debe elevar `confidence` sin reglas explicitas.
- No debe transformar `pending_review` en evidencia fuerte.
- No debe transformar notas locales en literatura verificada.
- No debe transformar `include_for_structure_check` en validacion biologica.
- Debe preservar `organism`.
- Debe preservar `strain`.
- Debe preservar `protein_id`.
- Debe preservar `gene`.
- Debe preservar `curator_name`.
- Debe preservar `curation_date`.
- Debe preservar `curation_decision`.
- Debe preservar `evidence_summary`.
- Debe preservar `evidence_status`.
- Debe preservar `source_database`.
- Debe preservar `reference_or_note`.
- Debe preservar `curator_notes`.
- Debe conservar `source_type=user_curated` o equivalente estructural si se
  transforma en el futuro.
- Debe distinguir `evidence_summary`, `evidence_status`, `curator_notes` y
  `reference_or_note`.
- Debe mantener separacion entre `therapeutic_priority_score` y
  `evidence_confidence_score`.
- Debe mantener separacion entre evidencia curada e inferencia automatica.
- Ausencia de evidencia no significa bajo riesgo.
- Evidencia pendiente no significa evidencia negativa.
- Evidencia manual no significa evidencia experimental.
- `user_curated` no equivale a `demo`.
- `user_curated` no equivale a `proxy`.
- `user_curated` no equivale a `cache`.
- `user_curated` no equivale a `controlled_reference`.
- No se introducen defaults de PAO1, H37Rv ni Corynebacterium.
- El sistema sigue siendo multi-organismo y theory-first.

## Criterios de aceptacion para futura transformacion

Una transformacion futura de `manual_curation.csv` solo sera aceptable si:

1. Tiene funcion pura separada.
2. Tiene prueba unitaria.
3. Preserva todos los campos criticos o los conserva en notas/provenance.
4. No ejecuta scoring.
5. No ejecuta `run_pipeline.py`.
6. No ejecuta modo online.
7. No genera ranking terapeutico.
8. No modifica `src/nodos_funcionales/scoring.py`.
9. No modifica `import_dataset.py` salvo justificacion explicita.
10. No modifica snapshots.
11. No modifica `results/`.
12. No modifica `data_processed/`.
13. No modifica `user_curated_staging/`.
14. No versiona `data_sessions/`.
15. Diferencia `evidence_quality` de `literature_support`.
16. No convierte `pending_review` en high confidence.
17. No convierte `local_note` en DOI o literatura verificada.
18. No interpreta `include_for_structure_check` como validacion experimental.
19. Conserva `organism`/`strain` sin usar defaults.
20. Pasa la suite offline.

## Estado de cierre

Estado: especificacion documental para mapeo de `manual_curation.csv` creada.
La siguiente fase puede implementar una transformacion minima solo si elige un
destino conceptual, documenta el mapeo exacto y mantiene separadas evidencia,
confianza, prioridad y procedencia.
