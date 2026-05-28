# User-curated minimal functional validation flow closure

## Proposito

Este cierre documenta la subfase `minimal functional validation flow`
`user_curated`. La prueba
`tests/test_user_curated_minimal_functional_validation_flow.py` valido que un
dataset minimo, realista y portable puede recorrer el flujo funcional completo:
manifest de usuario, importacion a `data_user`, resolucion como capas de
usuario, ejecucion offline del pipeline y generacion de reportes finales.

El flujo fue portable porque la prueba construyo todos los insumos dentro de un
temporary workspace / workspace temporal con `tmp_path`. No dependio de outputs
historicos, snapshots, `results/`, `data_processed/`, `data_sessions/` ni datos
demo preexistentes.

## Alcance biologico y operativo

El organismo usado en la prueba no esta acoplado a PAO1, H37Rv ni
Corynebacterium. El objetivo fue validar el funcionamiento del flujo
`user_curated`, no demostrar no clinical validation / no validacion clinica ni
no experimental validation / no validacion experimental.

Los datos `user_curated` representan evidencia aportada o revisada por el
usuario. Esa condicion conserva trazabilidad de curacion local, pero no equivale
automaticamente a verificacion externa, validacion clinica ni validacion
experimental.

## Procedencia y separacion de fuentes

La prueba verifico provenance / procedencia y separacion explicita entre:

- `user_curated`
- demo
- proxy
- cache
- online
- `controlled_reference`

La lectura esperada es que las capas importadas desde `data_user` se resuelvan
como evidencia de usuario, sin convertir demo, proxy, cache, online ni
`controlled_reference` en evidencia aportada por usuario.

## Lectura conservadora de reportes

Los reportes finales deben mantener conservative interpretation /
interpretacion conservadora. `therapeutic_priority_score` y
`evidence_confidence_score` se mantienen como metricas separadas:

- `therapeutic_priority_score` prioriza hipotesis terapeuticas dentro del
  modelo.
- `evidence_confidence_score` describe el soporte disponible para interpretar
  esa prioridad.

Insufficient evidence / evidencia insuficiente no equivale a bajo riesgo. Un
campo incompleto, una nota pendiente o una ausencia de evidencia no prueban
seguridad ni reducen automaticamente el riesgo.

Estados como `pending_review`, `local_note`, `curator_notes` u otros estados
similares preservan contexto de curacion, pero no elevan confianza por si
mismos. Tampoco deben convertirse en conclusiones afirmativas de seguridad o
validacion.

Por ese motivo, los reportes no deben presentar interpretaciones como
`safe_target`, `clinically_valid`, `validated_clinically` o
`validated_experimentally`.

## Cierre

Esta subfase fortalece la madurez operativa del pipeline porque confirma que un
flujo minimo `user_curated` puede ejecutarse de forma autocontenida hasta
reportes finales interpretables. No modifica `scoring.py`, no cambia la logica
cientifica de scoring y no regenera outputs historicos.
