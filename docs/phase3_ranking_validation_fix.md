# Correccion y validacion del ranking de Fase 3

## Proposito cientifico

Esta iteracion corrige la persistencia y el ordenamiento de `meta_priority_score_v3` para que el ranking de Fase 3 represente candidatos terapeuticos reales y no registros de plantilla o demo.

## Variables nuevas o fortalecidas

- `is_template_or_demo_record`: marca registros de ejemplo, plantilla o demo dominante.
- `template_or_demo_reason`: explica por que un registro fue marcado.
- `included_in_therapeutic_ranking`: indica si participa en el ranking terapeutico real.
- `rank_phase3_real_candidates`: rank solo entre candidatos reales.
- `rank_phase3_all_records`: rank del archivo completo, incluidos registros excluidos.
- `literature_support_status`: distingue evidencia bibliografica curada de plantillas vacias o pendientes.
- `literature_has_curated_evidence`: bandera booleana para soporte bibliografico real.

## Reglas de scoring y ranking

`meta_priority_score_v3` se calcula despues de las capas de Fase 3 y se valida antes de exportar. Si hay candidatos reales y todos quedan con score 0.0, se emite una advertencia explicita.

El orden de `ranking_nodos_phase3.csv` es:

1. candidatos incluidos primero;
2. `meta_priority_score_v3` descendente;
3. `evidence_quality_score` descendente;
4. `functional_node_theory_score` descendente;
5. `meta_priority_score_v2` descendente.

Los registros demo/template se conservan para auditoria, pero no reciben `rank_phase3_real_candidates`.

## Literature support

La capa `literature_support` no aumenta score ni confianza si solo contiene plantillas, ejemplos, `TO_BE_CURATED`, `pending_manual_curation` o referencias vacias. Solo aporta cuando hay DOI, PubMed ID, cita o referencia curada no marcada como demo/template.

## Outputs relevantes

- `results/ranking_nodos_phase3.csv`
- `results/ranking_nodos_phase3_real_candidates.csv`
- `results/template_or_demo_records.csv`
- `results/top10_scientific_audit.csv`
- `results/top10_scientific_audit.md`
- `results/report_phase3.md`

## Pruebas recomendadas

- `python -m pytest -m unit -q`
- `python -m pytest -m "not slow and not online" -q`
- `python -m pytest -m "online" -q` solo cuando se quiera validar proveedores externos.

## Limitaciones actuales

La ausencia de literatura curada se mantiene neutral: no penaliza como evidencia negativa ni aumenta confianza. La interpretacion biologica sigue siendo heuristica y requiere curacion experimental o bibliografica para validacion translacional.

## Pasos futuros sugeridos

Conectar evidencia bibliografica real de forma incremental detras del resolvedor de capas, empezando por fuentes estables con identificadores DOI/PubMed, y agregar curacion manual versionada para los candidatos reales mejor posicionados.
