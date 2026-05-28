# Internal release readiness 2026-05-27

## Estado general del proyecto

Nodos Funcionales cuenta con una base theory-first: la Teoria de Nodos
Funcionales organiza las decisiones de datos, scoring, reporting e
interpretacion. El software sirve a esa teoria como plataforma de priorizacion
terapeutica, no como predictor clinico definitivo / not a clinical predictor.

El flujo `user_curated` ya fue validado de forma portable. La validacion cubrio
un workspace temporal, importacion a `data_user`, ejecucion offline, generacion
de reportes finales y conservative interpretation / interpretacion
conservadora. El flujo mantiene orientacion multi-organism / multi-organismo y
no queda acoplado a PAO1, H37Rv ni Corynebacterium.

La suite offline completa pasa con:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

## Componentes listos para release interno

- Importacion y validacion de datos `user_curated`.
- Generacion de reportes finales.
- Separacion entre `therapeutic_priority_score` y
  `evidence_confidence_score`.
- Trazabilidad/provenance / procedencia de capas.
- Lectura conservadora de insufficient evidence / evidencia insuficiente.
- Separacion entre `user_curated`, demo, proxy, cache, online y
  `controlled_reference`.
- Auditoria de no acoplamiento a PAO1, H37Rv o Corynebacterium.
- Ejecucion offline reproducible.

## Componentes que no deben presentarse como terminados clinicamente

- No clinical validation / no validacion clinica.
- No experimental validation / no validacion experimental.
- No hay eficacia terapeutica demostrada.
- No hay seguridad clinica demostrada.
- No hay confirmacion automatica de blancos terapeuticos.
- `user_curated` no equivale automaticamente a evidencia externa verificada.

## Comandos minimos recomendados

```powershell
git status --short
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
git tag --list "*user-curated*"
git log --oneline -10
```

## Riesgos interpretativos que deben conservarse

- Score alto no equivale automaticamente a confianza alta.
- Insufficient evidence / evidencia insuficiente no equivale a bajo riesgo.
- `pending_review`, `local_note`, `curator_notes` e
  `include_for_structure_check` no elevan confianza por si mismos.
- demo, proxy, cache, online y `controlled_reference` no equivalen a evidencia
  `user_curated`.
- La ausencia de evidencia no debe interpretarse como seguridad.

Estos limites deben mantenerse visibles en reportes, documentacion y cualquier
guia de uso. Tambien deben mantenerse separados de `scoring.py`: este readiness
no modifica scoring ni logica cientifica.

## Siguiente fase recomendada

1. Preparar guia de uso para un usuario real.
2. Preparar checklist de dataset `user_curated` minimo.
3. Preparar ejemplo de ejecucion limpia.
4. Solo despues considerar empaquetamiento o interfaz.

La siguiente fase deberia seguir priorizando reproducibilidad, trazabilidad e
interpretacion conservadora antes que nuevas capacidades visibles.
