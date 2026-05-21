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
La primera especificacion documental de ese paso esta en
`docs/user_curated_controlled_scoring_spec.md`.

## Manual approval JSON templates for local GUI review

The local GUI can review manual approval JSON records for future controlled scoring. This review is visual and conservative only: it does not execute scoring, does not run the pipeline, does not generate rankings, and does not write scientific outputs.

Example templates are available in docs/templates/scoring_approval/: approved_for_controlled_scoring.example.json, rejected_for_scoring.example.json, and requires_additional_curation.example.json.

During a local GUI demo, the reviewer can upload each JSON file in the manual approval section and confirm that the approved example allows a future controlled scoring step but does not execute it, the rejected example blocks controlled scoring, and the additional-curation example blocks controlled scoring until curation is completed.

The approved template is only a demonstration of the approval-gate mechanism. It must be replaced with a real expert-reviewed record before any future controlled scoring workflow.
