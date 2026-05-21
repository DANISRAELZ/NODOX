# User-Curated GUI Final Closure

## Proposito

La GUI opcional `user_curated` cierra una fase de onboarding visual seguro para
preparar datasets revisables antes de cualquier scoring. Ayuda a ordenar el
staging local, el manifest, la evidencia, el quality gate y la revision experta
sin convertir la interfaz en pipeline, scoring o ranking.

## Cobertura cerrada

La fase de interfaz grafica cubre:

1. staging local;
2. revision de archivos locales;
3. validacion de manifest;
4. revision de evidencia y `provenance`;
5. quality gate previo a scoring;
6. resumen experto exportable;
7. importacion validada asistida como comando manual;
8. demo local controlada.

La secuencia operativa detallada sigue documentada en
`docs/user_curated_gui_onboarding.md`, y la demo local controlada en
`docs/user_curated_gui_local_demo_checklist.md`.

## Tags principales de estabilidad

- `user-curated-gui-pre-scoring-quality-gate-release-2026-05-21`
- `user-curated-gui-expert-review-summary-release-2026-05-21`
- `user-curated-gui-full-workflow-review-release-2026-05-21`
- `user-curated-gui-local-demo-workflow-release-2026-05-21`
- `user-curated-gui-local-demo-verified-2026-05-21`

## Limites conservados

La GUI:

- no ejecuta scoring;
- no ejecuta pipeline;
- no genera rankings;
- no modifica `results/`, `data_processed/`, `data_sessions/` ni snapshots;
- no sustituye scripts, configuracion o contratos cientificos del pipeline.

`user_curated` permanece separado de demo, proxy, cache,
`controlled_reference` y online. La interfaz sigue orientada a multiples
organismos y no introduce defaults de organismo o cepa especificos.

## Limites interpretativos

- Un manifest valido no equivale a validacion biologica.
- Un quality gate favorable no equivale a recomendacion terapeutica.
- Un score alto futuro no equivale automaticamente a confianza alta.
- La GUI no sustituye revision experta ni validacion experimental.

## Siguiente paso futuro

El siguiente paso debe ser una fase separada y explicitamente aprobada. Puede
definir como revisar paquetes `user_curated` ya preparados antes de una futura
importacion o corrida controlada, manteniendo separacion estricta entre
confianza de evidencia, priorizacion computacional y validacion experimental.
