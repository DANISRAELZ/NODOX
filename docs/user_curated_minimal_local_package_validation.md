# User-curated minimal local package validation

## Propósito

Este documento registra el cierre local mínimo de un paquete `user_curated`. El contenido real del paquete no se versiona; solo se documentan estructura, trazabilidad y prevalidación.

## Paquete local

```text
user_curated_staging/minimal_user_curated_validation_01/
```

`user_curated_staging/` permanece ignorado por Git y no debe versionarse.

## Estructura verificada

El paquete contiene:

- `README.md`
- `manifest.csv`
- `raw_inputs/`
- `provenance/`
- `notes/`

Dentro de `raw_inputs/` se revisaron los archivos previstos para el paquete mínimo:

- `gene_list.csv`
- `manual_curation.csv`
- `functional_annotations.csv`
- `conservation.csv`
- `evolutionary_escape_risk.csv`

## Alcance ficticio y neutral

El manifest declara el organismo `Example bacterium` y el alcance `minimal_validation_scope`.

No se uso PAO1, H37Rv ni Corynebacterium como default. Los candidatos del paquete son ficticios y no constituyen evidencia clinica, experimental ni una recomendación terapéutica.

`source_type=user_curated` describe procedencia y revisión humana. En este paquete de validación solo representa estructura local y trazabilidad revisable; no convierte un fixture en evidencia biológica real.

## Prevalidación

### paso validacion por Python

Comando relativo para Windows con el entorno virtual del repositorio:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py user_curated_staging\minimal_user_curated_validation_01\manifest.csv
```

Comando equivalente con el intérprete activo:

```powershell
python scripts/validate_user_curated_manifest.py user_curated_staging/minimal_user_curated_validation_01/manifest.csv
```

### paso validacion por wrapper PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\minimal_user_curated_validation_01\manifest.csv
```

Resultado esperado:

```text
[OK] Manifest user_curated valido para revision/importacion.
[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring.
```

Esta prevalidacion no ejecuta pipeline, importacion ni scoring y no modifica `src/nodos_funcionales/scoring.py`.

## Garantías de no modificación

La validación no modifica:

- scoring;
- snapshots;
- `results/`;
- `data_processed/`;
- `data_sessions/`;
- `config/taxon_resolution_cache.json`.

Tampoco abre red, importa datos al pipeline ni genera rankings.

## Interpretación científica

`therapeutic_priority_score` y `evidence_confidence_score` deben permanecer separados.

Evidencia insuficiente no significa bajo riesgo. `evolutionary_escape_risk` actua como modulador interpretativo, no como certeza clinica.

`demo`, `proxy`, `cache`, `controlled_reference` y `user_curated` no son equivalentes y deben conservar etiquetas de procedencia distintas.

## Estado

El paquete mínimo fue preparado fuera del control de versiones y su manifest pasó prevalidación estructural. Cualquier importación, scoring o interpretación posterior requiere revisión humana y autorización explícita.
