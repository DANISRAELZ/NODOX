# Correccion y validacion del ranking de Fase 3

## Proposito cientifico

Esta iteracion corrige la persistencia y el ordenamiento de `meta_priority_score_v3` para que el ranking de Fase 3 represente candidatos terapeuticos reales y no registros de plantilla o demo.

## Variables nuevas o fortalecidas

- `is_template_or_demo_record`: marca registros de ejemplo, plantilla o demo dominante.
- `template_or_demo_reason`: explica por que un registro fue marcado.
- `included_in_therapeutic_ranking`: indica si participa en el ranking terapeutico real.
- `candidate_record_type`: clasifica `template_record`, `demo_record`, `real_candidate`, `mixed_evidence_candidate` o `insufficiently_supported_candidate`.
- `ranking_inclusion_status`: explica si el candidato entra como real, entra como exploratorio o queda excluido.
- `ranking_inclusion_reason`: razon corta y auditable de inclusion o exclusion.
- `real_evidence_layer_count`, `demo_or_default_layer_count`, `proxy_layer_count`, `missing_layer_count`: conteos por candidato usados para no confundir evidencia mixta con plantilla pura.
- `evidence_mixture_label`: resumen legible de la mezcla de evidencia.
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
5. `confidence_ceiling` descendente;
6. `meta_priority_score_v2` descendente.

Los registros demo/template se conservan para auditoria, pero no reciben `rank_phase3_real_candidates`. `EXAMPLE_PROTEIN` siempre queda excluido como registro de plantilla o demo.

Los umbrales default configurables en `config/params.yaml` son:

- `min_real_layers_for_exploratory_inclusion: 1`
- `min_real_layers_for_real_candidate: 3`
- `max_demo_fraction_for_real_candidate: 0.50`
- `allow_mixed_evidence_candidates: true`
- `exclude_explicit_template_records: true`
- `exclude_demo_only_records: true`

Un candidato con evidencia real parcial y soporte demo/proxy/default puede entrar como `included_exploratory_with_demo_support`. Esa inclusion no valida el candidato: solo evita perder candidatos exploratorios por una regla binaria demasiado agresiva.

## Literature support

La capa `literature_support` no aumenta score ni confianza si solo contiene plantillas, ejemplos, `TO_BE_CURATED`, `pending_manual_curation` o referencias vacias. Solo aporta cuando hay DOI, PubMed ID, cita o referencia curada no marcada como demo/template.

## Outputs relevantes

- `results/ranking_nodos_phase3.csv`
- `results/ranking_nodos_phase3_real_candidates.csv`
- `results/template_or_demo_records.csv`
- `results/top10_scientific_audit.csv`
- `results/top10_scientific_audit.md`
- `results/report_phase3.md`

## Estado interpretativo del export

Los reportes de Fase 3 deben separar el estado del export del valor biologico
del organismo evaluado:

- `ranking_real_produced`: hay candidatos incluidos en el ranking terapeutico
  real. Se interpretan junto con confianza, procedencia, evidencia faltante y
  riesgo evolutivo.
- `no_real_ranking_demo_template_or_insufficient_evidence`: el ranking real no
  se produjo porque las filas disponibles son demo/template, faltantes o
  insuficientes. Este estado es un resultado esperado y correcto cuando solo hay
  fixtures, plantillas o evidencia incompleta.
- `no_evaluable_candidates_with_traceable_negative_evidence`: no hay candidatos
  evaluables por evidencia negativa trazable en las filas presentes. Esto no
  prueba ausencia biologica fuera del alcance de esas fuentes.
- `no_phase3_records`: no hay filas para auditar.

En todos los estados, ausencia o insuficiencia de evidencia no equivale a
evidencia negativa, bajo riesgo, ausencia biologica ni irrelevancia terapeutica.
Demo, proxy, cache o referencia controlada tampoco sustituyen evidencia real del
usuario ni evidencia externa trazable.

## Pruebas recomendadas

- `python -m pytest -m unit -q`
- `python -m pytest -m "not slow and not online and not e2e" -q`
- `python -m pytest -m "online" -q` solo cuando se quiera validar proveedores externos.

## Limitaciones actuales

La ausencia de literatura curada se mantiene neutral: no penaliza como evidencia negativa ni aumenta confianza. La interpretacion biologica sigue siendo heuristica y requiere curacion experimental o bibliografica para validacion translacional.

## Pasos futuros sugeridos

Conectar evidencia bibliografica real de forma incremental detras del resolvedor de capas, empezando por fuentes estables con identificadores DOI/PubMed, y agregar curacion manual versionada para los candidatos reales mejor posicionados.
