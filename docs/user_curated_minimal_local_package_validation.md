# User-curated minimal local package validation

## Propósito

Este documento registra una validación local mínima de un paquete `user_curated`. El contenido real del paquete no se versiona; solo se documentan su estructura, trazabilidad y prevalidación.

## Paquete local

```text
user_curated_staging/minimal_user_curated_validation_01/
```

`user_curated_staging/` permanece ignorado por Git y no debe versionarse.

## Estructura verificada

- `README.md`
- `manifest.csv`
- `raw_inputs/`
- `provenance/`
- `notes/`

Los datos utilizados fueron ficticios y se identificaron como `Example bacterium`, con candidatos `candidate_A`, `candidate_B` y `candidate_C`. No constituyen evidencia clínica, experimental ni recomendación terapéutica.

## Prevalidación

```powershell
python scripts/validate_user_curated_manifest.py user_curated_staging/minimal_user_curated_validation_01/manifest.csv
```

Wrapper PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging/minimal_user_curated_validation_01/manifest.csv
```

Resultado esperado:

```text
[OK] Manifest user_curated valido para revision/importacion.
[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring.
```

## Garantías

La validación no modifica scoring, snapshots, resultados, datos procesados, sesiones ni cache taxonómica. No abre red ni genera ranking.

`source_type=user_curated` describe procedencia y revisión, pero no convierte datos ficticios en evidencia biológica real. Prioridad terapéutica y confianza de evidencia deben permanecer separadas.

## Estado

El paquete mínimo fue preparado fuera del control de versiones y su manifest pasó prevalidación estructural. Cualquier fase posterior requiere revisión humana y autorización explícita.
