# User-curated manual curation import check

## Proposito

Este documento registra la importacion controlada de la salida transformada
`manual_curation -> evidence_quality` como capa `user_curated`, sin scoring,
sin pipeline, sin modo online y sin ranking terapeutico.

La transformacion `manual_curation -> evidence_quality` ya estaba implementada
y testeada en:

```text
src/nodos_funcionales/user_curated_transformations.py
tests/test_user_curated_manual_curation_transformation.py
docs/user_curated_manual_curation_transformation.md
```

Esta fase solo verifico la importacion controlada de la salida transformada.

## Entrada y workspace

Entrada local ignorada por Git:

```text
user_curated_staging/minimal_user_curated_validation_01/raw_inputs/manual_curation.csv
```

Manifest local:

```text
user_curated_staging/minimal_user_curated_validation_01/manifest.csv
```

Workspace dedicado:

```text
data_sessions/minimal_user_curated_manual_curation_import_check
```

El workspace es temporal, local y no debe versionarse como evidencia estable.

## Transformacion temporal

Se uso la funcion pura:

```python
transform_user_curated_manual_curation_to_evidence_quality(...)
```

La tabla transformada se guardo temporalmente dentro del workspace dedicado:

```text
data_sessions/minimal_user_curated_manual_curation_import_check/tmp_transformed/evidence_quality.csv
```

La transformacion preservo `gene`, `protein_id`, `evidence_quality_score`,
`confidence_ceiling`, `evidence_source_type`, `evidence_notes`, `audit_flags`,
`phase3_notes` y `database`.

## Importacion controlada

Comando ejecutado:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "Example bacterium" --strain "minimal_validation_scope" --workspace data_sessions\minimal_user_curated_manual_curation_import_check --dataset evidence_quality --input data_sessions\minimal_user_curated_manual_curation_import_check\tmp_transformed\evidence_quality.csv --validate-user-curated-manifest user_curated_staging\minimal_user_curated_validation_01\manifest.csv --as-user-layer
```

Resultado observado:

```text
[OK] Manifest user_curated valido para revision/importacion.
[OK] Organismo: Example bacterium
[OK] Cepa: minimal_validation_scope
[OK] Dataset importado: evidence_quality
[OK] Destino como capa de usuario: data_user
[OK] Destino: data_sessions\minimal_user_curated_manual_curation_import_check\data_user\evidence_quality.csv
[OK] Filas fuente: 3; filas mapeadas: 3
[OK] Copia del export original: data_sessions\minimal_user_curated_manual_curation_import_check\data_user\source_exports\evidence_quality.csv
```

## Archivos generados localmente

La comprobacion genero archivos solo dentro del workspace dedicado:

```text
data_sessions/minimal_user_curated_manual_curation_import_check/config/params.yaml
data_sessions/minimal_user_curated_manual_curation_import_check/tmp_transformed/evidence_quality.csv
data_sessions/minimal_user_curated_manual_curation_import_check/data_user/evidence_quality.csv
data_sessions/minimal_user_curated_manual_curation_import_check/data_user/source_exports/evidence_quality.csv
```

El archivo importado como capa de usuario fue:

```text
data_sessions/minimal_user_curated_manual_curation_import_check/data_user/evidence_quality.csv
```

Esto verifica que la salida transformada puede importarse como
`evidence_quality` `user_curated`.

## Trazabilidad preservada

La capa importada preservo:

- `gene`;
- `protein_id`;
- `organism=Example bacterium` dentro de `database`;
- `strain=minimal_validation_scope` dentro de `database`;
- `curator_name=Nodos local curator` dentro de `database`;
- `curation_date=2026-05-24` dentro de `database`;
- `source_database=user_curated_local_note` dentro de `database`;
- `source_type=user_curated` dentro de `database`;
- `curation_decision=include_for_structure_check` dentro de `evidence_notes`;
- `evidence_summary=...` dentro de `evidence_notes`;
- `evidence_status=pending_review` dentro de `evidence_notes`;
- `reference_or_note=Local validation note only` dentro de `evidence_notes`;
- `curator_notes=...` dentro de `evidence_notes`.

La copia original del export transformado tambien quedo en:

```text
data_user/source_exports/evidence_quality.csv
```

## Garantias interpretativas

La capa `evidence_quality` importada sigue siendo `user_curated` o derivada de
`user_curated`. No equivale a `demo`, `proxy`, `cache` ni
`controlled_reference`.

`manual_curation` no equivale automaticamente a prioridad terapeutica.
`evidence_quality` apoya interpretacion de evidencia, no ranking terapeutico.

`pending_review` no equivale a alta confianza. En esta comprobacion,
`evidence_quality_score` y `confidence_ceiling` quedaron como valores
conservadores de `0.2`.

`include_for_structure_check` no equivale a validacion experimental.
`local_note` o `Local validation note only` no equivale a DOI ni literatura
verificada.

`therapeutic_priority_score` y `evidence_confidence_score` siguen separados.
Esta importacion no calcula ni modifica ninguno de esos scores.

No se genero ranking ni recomendacion clinica.

## Garantias de ejecucion

Durante esta fase:

- no se ejecuto scoring;
- no se ejecuto `run_pipeline.py`;
- no se ejecuto modo online;
- no se genero ranking terapeutico;
- no se modifico `src/nodos_funcionales/scoring.py`;
- no se modifico `import_dataset.py`;
- no se modifico `run_pipeline.py`;
- no se modificaron snapshots;
- no se modifico `results/`;
- no se modifico `data_processed/`;
- no se modifico `config/taxon_resolution_cache.json` como cambio final;
- no se modifico ni versiono `user_curated_staging/`;
- no se versiono `data_sessions/`.

## Estado de cierre

Estado: importacion controlada de `manual_curation` transformada a
`evidence_quality` verificada en workspace dedicado, sin scoring, sin pipeline,
sin modo online, sin ranking y sin versionar datos locales ni workspaces
temporales.
