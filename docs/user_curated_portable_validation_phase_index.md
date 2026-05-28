# User-curated portable validation phase index

## Proposito de la fase

Esta fase consolida la portable validation `user_curated`: valida que un flujo
de usuario pueda ejecutarse de forma portable, offline, trazable y
multi-organism / multi-organismo sin modificar la logica cientifica del
pipeline.

La fase confirma:

- flujo `user_curated` portable desde `workspace/data_user`;
- ejecucion offline del pipeline;
- generacion de reportes finales interpretables;
- conservative interpretation / interpretacion conservadora;
- desacoplamiento multi-organismo frente a PAO1, H37Rv y Corynebacterium.

## Subfases cerradas

| Commit | Tag | Proposito |
| --- | --- | --- |
| `dbfa079` | `user-curated-pipeline-integration-validation-2026-05-27` | Validacion de integracion `user_curated` a traves del pipeline. |
| `470ba33` | `user-curated-final-reporting-interpretation-validation-2026-05-27` | Validacion de interpretacion de reportes finales `user_curated`. |
| `14df878` | `user-curated-final-reporting-interpretation-closure-2026-05-27` | Cierre documental de la interpretacion final. |
| `9058e72` | `user-curated-minimal-functional-validation-flow-2026-05-27` | Validacion funcional minima portable `user_curated`. |
| `8841909` | `user-curated-minimal-functional-validation-flow-closure-2026-05-27` | Cierre documental del flujo funcional minimo portable. |
| `504c1af` | `user-curated-multiorganism-decoupling-audit-2026-05-27` | Auditoria de desacoplamiento multi-organismo. |

## Que quedo validado

- Construccion de `workspace/data_user` temporal.
- Uso de fixture autocontenido.
- Organismo no acoplado a PAO1 ni H37Rv.
- No dependencia de Corynebacterium.
- Separacion entre `user_curated`, demo, proxy, cache, online y
  `controlled_reference`.
- Conservacion de provenance / procedencia `user`, `user_curated` y
  `local_review`.
- Separacion entre `therapeutic_priority_score` y
  `evidence_confidence_score`.
- Generacion de reportes finales.
- Lectura conservadora de insufficient evidence / evidencia insuficiente.
- Rechazo de lenguaje indebido como `safe_target`, `clinically_valid`,
  `validated_clinically` y `validated_experimentally`.

## Que no quedo validado

- No clinical validation / no validacion clinica.
- No experimental validation / no validacion experimental.
- No demuestra eficacia terapeutica.
- No demuestra seguridad clinica.
- No convierte insufficient evidence / evidencia insuficiente en bajo riesgo.
- No convierte `user_curated` en evidencia externa verificada automaticamente.
- No convierte `pending_review`, `local_note`, `curator_notes` ni
  `include_for_structure_check` en alta confianza.

## Estado tecnico

- La suite offline completa paso.
- Los cambios de `config/taxon_resolution_cache.json` por timestamps,
  `updated_at_utc`, `saved_at_utc` o `refresh_count` fueron revertidos.
- El working tree quedo limpio al cierre de cada subfase.
- No se modifico `scoring.py`.
- No se regeneraron outputs historicos, snapshots, `results/`,
  `data_processed/` ni `data_sessions/`.

## Relevancia para la Teoria de Nodos Funcionales

Esta fase refuerza el enfoque multi-organismo de la Teoria de Nodos
Funcionales. PAO1, H37Rv y Corynebacterium pueden funcionar como ejemplos,
fixtures o referencias de fases anteriores, pero no son defaults cientificos
obligatorios del flujo `user_curated`.

El software sirve a la teoria: organiza evidencia, preserva procedencia y ayuda
a la therapeutic prioritization / priorizacion terapeutica graduada, trazable y
conservadora. No sustituye la validacion experimental ni convierte resultados
del pipeline en afirmaciones clinicas automaticas.

La subcapa evolutiva, la procedencia, la confianza de evidencia y la lectura de
riesgo se mantienen como elementos interpretativos. No son pruebas clinicas,
no son validacion experimental y no deben leerse como seguridad o eficacia
definitiva.
