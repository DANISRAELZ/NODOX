# User-curated conservation import check

## Proposito

Este documento registra la importacion controlada de la salida transformada
`conservation -> strain_conservation` como capa `user_curated`, sin scoring,
sin pipeline, sin modo online y sin ranking terapeutico.

La transformacion `conservation -> strain_conservation` ya estaba implementada
y testeada en:

```text
src/nodos_funcionales/user_curated_transformations.py
tests/test_user_curated_conservation_transformation.py
docs/user_curated_conservation_transformation.md
```

Esta fase solo verifico la importacion controlada de la salida transformada.

## Entrada y workspace

Entrada local ignorada por Git:

```text
user_curated_staging/minimal_user_curated_validation_01/raw_inputs/conservation.csv
```

Manifest local:

```text
user_curated_staging/minimal_user_curated_validation_01/manifest.csv
```

Workspace dedicado:

```text
data_sessions/minimal_user_curated_conservation_import_check
```

El workspace es temporal, local y no debe versionarse como evidencia estable.

## Transformacion temporal

Se uso la funcion pura:

```python
transform_user_curated_conservation_to_strain_conservation(...)
```

La tabla transformada se guardo temporalmente dentro del workspace dedicado:

```text
data_sessions/minimal_user_curated_conservation_import_check/tmp_transformed/strain_conservation.csv
```

La transformacion preservo `gene`, `protein_id`, `core_genome_presence`,
`strain_coverage_score`, `allelic_conservation`, `variant_burden` y trazabilidad
en `database`.

Como `strain_conservation_template.csv` no tiene columnas separadas para
`organism`, `strain`, `source_type`, `evidence_status` ni `curator_notes`, esos
metadatos quedaron preservados en `database` como procedencia auditable:

```text
source_database=...; source_type=user_curated; organism=...; strain=...; conservation_scope=...; evidence_status=...; curator_notes=...
```

## Importacion controlada

Comando ejecutado:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "Example bacterium" --strain "minimal_validation_scope" --workspace data_sessions\minimal_user_curated_conservation_import_check --dataset strain_conservation --input data_sessions\minimal_user_curated_conservation_import_check\tmp_transformed\strain_conservation.csv --validate-user-curated-manifest user_curated_staging\minimal_user_curated_validation_01\manifest.csv --as-user-layer
```

Resultado observado:

```text
[OK] Manifest user_curated valido para revision/importacion.
[OK] Organismo: Example bacterium
[OK] Cepa: minimal_validation_scope
[OK] Dataset importado: strain_conservation
[OK] Destino como capa de usuario: data_user
[OK] Destino: data_sessions\minimal_user_curated_conservation_import_check\data_user\strain_conservation.csv
[OK] Filas fuente: 3; filas mapeadas: 3
[OK] Copia del export original: data_sessions\minimal_user_curated_conservation_import_check\data_user\source_exports\strain_conservation.csv
```

## Archivos generados localmente

La comprobacion genero archivos solo dentro del workspace dedicado:

```text
data_sessions/minimal_user_curated_conservation_import_check/config/params.yaml
data_sessions/minimal_user_curated_conservation_import_check/tmp_transformed/strain_conservation.csv
data_sessions/minimal_user_curated_conservation_import_check/data_user/strain_conservation.csv
data_sessions/minimal_user_curated_conservation_import_check/data_user/source_exports/strain_conservation.csv
```

El archivo importado como capa de usuario fue:

```text
data_sessions/minimal_user_curated_conservation_import_check/data_user/strain_conservation.csv
```

Esto verifica que la salida transformada puede importarse como
`strain_conservation` `user_curated`.

## Trazabilidad preservada

La capa importada preservo:

- `gene`;
- `protein_id`;
- `organism=Example bacterium` dentro de `database`;
- `strain=minimal_validation_scope` dentro de `database`;
- `source_database=user_curated_local_note` dentro de `database`;
- `source_type=user_curated` dentro de `database`;
- `evidence_status=pending_review` dentro de `database`;
- `curator_notes=...` dentro de `database`;
- incertidumbre como `unknown`, `limited`, `variable`, `moderate` o notas de
  riesgo no resuelto, sin reinterpretarla como bajo riesgo.

## Garantias

Durante esta fase:

- no se ejecuto scoring;
- no se ejecuto `run_pipeline.py`;
- no se ejecuto modo online;
- no se genero ranking terapeutico;
- no se modifico `src/nodos_funcionales/scoring.py`;
- no se modifico `run_pipeline.py`;
- no se modificaron snapshots;
- no se modifico `results/`;
- no se modifico `data_processed/`;
- no se modifico `config/taxon_resolution_cache.json` como cambio final;
- no se modifico ni versiono `user_curated_staging/`;
- no se versiono `data_sessions/`.

## Interpretacion permitida

La capa `strain_conservation` importada sigue siendo `user_curated` o derivada
de `user_curated`. No equivale a `demo`, `proxy`, `cache` ni
`controlled_reference`.

La conservacion no equivale automaticamente a prioridad terapeutica.
`core_genome_presence=true` no significa alta prioridad terapeutica, y
`core_genome_presence=false` no significa bajo riesgo evolutivo.

Evidencia incompleta no significa bajo riesgo. `unknown`, valores descriptivos
y notas de curacion deben leerse como incertidumbre o riesgo no resuelto.

`therapeutic_priority_score` y `evidence_confidence_score` siguen separados.
Esta importacion no calcula ni modifica ninguno de esos scores.

Esta fase no equivale a evidencia clinica y debe revisarse antes de usar la
capa en una corrida real.

## Estado de cierre

Estado: importacion controlada de conservacion transformada verificada en
workspace dedicado, sin scoring, sin pipeline, sin modo online, sin ranking y
sin versionar datos locales ni workspaces temporales.
