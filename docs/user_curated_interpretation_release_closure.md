# User-curated interpretation release closure

## Proposito

Este cierre deja estable el bloque interpretativo `user_curated` como release.
El bloque agrega lectura de resultados, auditoria de procedencia y exportacion
de explicaciones, pero no agrega scoring nuevo. Es una capa interpretativa:
no modifica `src/nodos_funcionales/scoring.py`, pesos, formulas, ranking ni
ordenamiento de candidatos.

## Fases cerradas

| Fase | Commit | Tag |
| --- | --- | --- |
| Document user-curated end-to-end evidence flow | `c623b4b` | `user-curated-end-to-end-flow-docs-release-2026-05-23` |
| Validate minimal user-curated end-to-end dataset flow | `9832120` | `user-curated-minimal-end-to-end-validation-release-2026-05-23` |
| Guard user-curated score confidence interpretation | `44568b3` | `user-curated-score-confidence-guards-release-2026-05-23` |
| Add conservative interpretation mode | `fb08d90` | `conservative-interpretation-mode-release-2026-05-23` |
| Add final interpretation matrix | `492b03d` | `final-interpretation-matrix-release-2026-05-23` |
| Export final interpretation matrix | `d6c22ba` | `final-interpretation-matrix-export-release-2026-05-23` |
| Audit user-curated interpretation closure | `80292d2` | `user-curated-interpretation-closure-audit-release-2026-05-23` |

## Componentes disponibles

- `docs/user_curated_end_to_end_flow.md`: flujo completo de evidencia
  `user_curated`.
- `tests/fixtures/user_curated_minimal_dataset/`: fixture minimo end-to-end.
- `score_confidence_interpretation`: separa `therapeutic_priority_score` de
  `evidence_confidence_score`.
- `conservative_interpretation`: lectura conservadora interpretativa.
- `final_interpretation_matrix`: matriz score/confianza/riesgo/procedencia.
- `tests/test_user_curated_interpretation_closure_audit.py`: auditoria
  documental y funcional de cierre interpretativo.
- `tests/test_final_interpretation_exports.py`: prueba de exportacion de la
  matriz final.
- `docs/user_curated_interpretation_closure_audit.md`: auditoria de cierre del
  bloque interpretativo.

## Garantias del bloque

El bloque garantiza que:

- no modifica `src/nodos_funcionales/scoring.py`;
- no modifica pesos;
- no modifica formulas;
- no modifica ranking ni ordenamiento;
- no convierte demo, proxy ni cache en evidencia real;
- mantiene `user_curated` separado de demo, proxy, cache,
  `controlled_reference` y online;
- mantiene orientacion multiorganismo;
- mantiene advertencias sobre evidencia insuficiente, riesgo evolutivo incierto
  y validacion experimental;
- exportar `final_interpretation_matrix` no modifica la interpretacion, el
  score ni la prioridad.

## Limites

Nodos Funcionales sigue siendo una plataforma de priorizacion terapeutica, no
una herramienta clinica ni predictor definitivo. No sustituye validacion
experimental.

Lecturas obligatorias:

- score alto no equivale automaticamente a confianza alta;
- confianza alta no equivale automaticamente a prioridad terapeutica alta;
- ausencia de evidencia no equivale a bajo riesgo;
- evidencia insuficiente no equivale a bajo riesgo;
- riesgo evolutivo incierto no equivale a bajo riesgo evolutivo;
- demo, proxy y cache no equivalen a evidencia real;
- `controlled_reference` no es evidencia de usuario;
- `user_curated` requiere trazabilidad.

## Estado recomendado

Estado de cierre: bloque `user_curated interpretation` estable, documentado,
probado y tagueado. La siguiente fase posible puede ser GUI, scoring conservador
real, validacion con dataset real externo o generacion de reporte ejecutivo.
Esas fases deben seguir preservando la separacion entre interpretacion,
evidencia, scoring y validacion experimental.
