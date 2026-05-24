# User-curated minimal local package validation

## Proposito

Este documento registra el cierre documental de la primera validacion local
minima de paquete `user_curated`. El contenido del paquete local no se
versiona: solo se documenta que fue creado, que mantiene trazabilidad minima y
que su manifest paso prevalidacion estructural.

## Paquete local creado

Se creo el paquete local:

```text
user_curated_staging/minimal_user_curated_validation_01/
```

El directorio `user_curated_staging/` permanece ignorado por Git mediante
`.gitignore` y no debe versionarse. Esta regla evita convertir insumos locales
de usuario en artefactos del repositorio.

## Estructura verificada

El paquete local contiene:

- `README.md`;
- `manifest.csv`;
- `raw_inputs/`;
- `provenance/`;
- `notes/`.

Los `raw_inputs` incluyeron:

- `gene_list.csv`;
- `manual_curation.csv`;
- `functional_annotations.csv`;
- `conservation.csv`;
- `evolutionary_escape_risk.csv`.

## Alcance biologico declarado

El organismo usado fue generico de prueba:

- organism: `Example bacterium`;
- strain/scope: `minimal_validation_scope`.

No se uso PAO1, H37Rv ni Corynebacterium como default. El alcance biologico fue
declarado de forma explicita para esta validacion local y no debe inferirse a
partir de organismos modelo, datos demo, cache, proxies ni referencias
controladas.

Los candidatos del paquete son ficticios y metodologicamente utiles para
validar estructura:

- `candidate_A`;
- `candidate_B`;
- `candidate_C`.

Estos candidatos no constituyen evidencia clinica, evidencia experimental ni
recomendacion terapeutica.

## Manifest y prevalidacion

El `manifest.csv` declaro:

- `dataset_id=minimal_user_curated_validation_01`;
- `source_type=user_curated`;
- procedencia local clara y revisable;
- organismo y strain/scope definidos por usuario;
- schema/template usado por archivo;
- archivo asociado;
- estado de revision;
- notas indicando que es un dataset minimo de validacion local, no evidencia
  clinica.

El manifest paso validacion por Python:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py user_curated_staging\minimal_user_curated_validation_01\manifest.csv
```

Resultado registrado:

```text
[OK] Manifest user_curated valido para revision/importacion.
[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring.
```

El manifest tambien paso validacion por wrapper PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\minimal_user_curated_validation_01\manifest.csv
```

Resultado registrado:

```text
[OK] Python: C:\Users\danis\OneDrive\Escritorio\nodos\.venv\Scripts\python.exe
[OK] Prevalidando manifest user_curated: user_curated_staging\minimal_user_curated_validation_01\manifest.csv
[INFO] Esta revision no ejecuta importacion, pipeline ni scoring.
[OK] Manifest user_curated valido para revision/importacion.
[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring.
```

Esta prevalidacion no ejecuta pipeline, importacion ni scoring.

## Garantias conservadas

La validacion local no modifica:

- `src/nodos_funcionales/scoring.py`;
- snapshots;
- `results/`;
- `data_processed/`;
- `data_sessions/`;
- `config/taxon_resolution_cache.json`.

No se ejecuto modo online. No se genero ranking, salida terapeutica real ni
dataset versionado.

## Interpretacion permitida

`source_type=user_curated` en este paquete solo representa estructura local y
trazabilidad revisable. No transforma candidatos ficticios en evidencia
biologica real ni clinica.

`therapeutic_priority_score` y `evidence_confidence_score` deben permanecer
separados en cualquier fase posterior. Una prioridad terapeutica modelada no
equivale automaticamente a confianza alta, y una confianza limitada no debe
ocultarse dentro del score terapeutico.

Evidencia insuficiente no significa bajo riesgo. Los faltantes deben leerse
como incertidumbre o riesgo no resuelto, no como evidencia negativa.

`evolutionary_escape_risk` actua como modulador interpretativo de riesgo, no
como certeza clinica ni predictor definitivo.

`demo`, `proxy`, `cache`, `controlled_reference` y `user_curated` no son
equivalentes. Deben permanecer separados en procedencia, lectura y reportes.

## Estado de cierre

Estado: paquete local minimo creado, ignorado por Git y prevalidado por manifest
con Python y PowerShell. La siguiente fase puede documentar o implementar una
validacion estructural mas amplia, siempre sin ejecutar scoring hasta que el
usuario apruebe explicitamente una corrida controlada.
