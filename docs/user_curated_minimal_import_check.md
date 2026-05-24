# User-curated minimal import check

## Proposito

Este documento registra la fase de importacion controlada de una primera capa
`user_curated` desde el paquete local ignorado por Git:

```text
user_curated_staging/minimal_user_curated_validation_01/
```

La fase verifica trazabilidad de importacion como capa de usuario. No produce
ranking terapeutico, no ejecuta scoring y no ejecuta `run_pipeline.py`.

## Seleccion de capa

La revision de `import_dataset.py --help` mostro que `gene_list` no es dataset
interno aceptado por `import_dataset.py`.

Los datasets aceptados por el importador son:

```text
clinical_impact, collateral_sensitivity, contextual_essentiality,
curated_disease_context, essentiality, evidence_quality, evolutionary_escape,
evolutionary_escape_risk, functional_network, host_annotation, human_homologs,
literature_support, localization, redundancy, strain_conservation,
therapy_site_context, virulence.
```

Por esa razon no se forzo `gene_list`. Se eligio
`evolutionary_escape_risk` porque es un dataset aceptado y esta alineado con la
subcapa evolutiva ya documentada para interpretar riesgo de escape.

## Workspace dedicado

La importacion fue una prueba local controlada en un workspace dedicado:

```text
data_sessions/minimal_user_curated_validation_01_import_check
```

Este workspace es temporal y no debe versionarse como evidencia estable.
`data_sessions/` permanece reservado para salidas locales o sesiones de prueba,
no para evidencia curada versionada.

## Comando ejecutado

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "Example bacterium" --strain "minimal_validation_scope" --workspace data_sessions\minimal_user_curated_validation_01_import_check --dataset evolutionary_escape_risk --input user_curated_staging\minimal_user_curated_validation_01\raw_inputs\evolutionary_escape_risk.csv --validate-user-curated-manifest user_curated_staging\minimal_user_curated_validation_01\manifest.csv --as-user-layer
```

El organismo fue generico de prueba:

- organism: `Example bacterium`;
- strain/scope: `minimal_validation_scope`.

No se uso PAO1, H37Rv ni Corynebacterium como default.

## Archivos generados

La importacion genero:

```text
data_sessions/minimal_user_curated_validation_01_import_check/config/params.yaml
data_sessions/minimal_user_curated_validation_01_import_check/data_user/evolutionary_escape_risk.csv
data_sessions/minimal_user_curated_validation_01_import_check/data_user/source_exports/evolutionary_escape_risk.csv
```

Esto verifica una primera importacion como capa de usuario:

- la capa interna quedo en `data_user/evolutionary_escape_risk.csv`;
- el export original quedo copiado en
  `data_user/source_exports/evolutionary_escape_risk.csv`;
- la importacion uso `--as-user-layer`;
- las filas conservan `source_type=user_curated` en la capa importada y en el
  export original.

## Garantias de no ejecucion

Durante esta fase:

- no se ejecuto scoring;
- no se ejecuto `run_pipeline.py`;
- no se produjo ranking terapeutico;
- no se uso modo online;
- no se modifico `src/nodos_funcionales/scoring.py`;
- no se modificaron snapshots;
- no se modifico `results/`;
- no se modifico `data_processed/`;
- no se modifico `config/taxon_resolution_cache.json` como cambio final;
- no se versiono `user_curated_staging/`;
- no se versiono el workspace bajo `data_sessions/`.

## Interpretacion permitida

Esta fase no busca producir una conclusion terapeutica. Solo confirma que una
capa local `user_curated` puede importarse de forma trazable, separada de
`demo`, `proxy`, `cache` y `controlled_reference`.

`user_curated` no equivale a `demo`, `proxy`, `cache` ni
`controlled_reference`. En esta fase, `source_type=user_curated` representa
procedencia local revisable y estructura de importacion, no evidencia clinica.

`therapeutic_priority_score` y `evidence_confidence_score` siguen separados.
La importacion no calcula ninguno de esos scores y no debe mezclarlos en una
lectura unica.

`evolutionary_escape_risk` es modulador interpretativo de riesgo, no certeza
clinica. Evidencia insuficiente no significa bajo riesgo; significa que el
riesgo queda no resuelto o requiere revision adicional.

## Estado de cierre

Estado: primera capa local `user_curated` importada de forma controlada como
user layer, sin scoring, sin pipeline, sin modo online y sin versionar insumos
locales ni el workspace temporal.
