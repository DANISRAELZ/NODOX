# Real User-Curated Dataset Validation

## Proposito

Esta fase valida que Nodos Funcionales pueda recibir datos reales aportados o
revisados por el usuario, importarlos como capas `user_curated`, conservar su
procedencia y generar reportes interpretables. La validacion no convierte esos
datos en evidencia externa verificada automaticamente y no demuestra eficacia
terapeutica.

## Alcance

Incluye:

- validacion de estructura de plantillas y manifest;
- importacion controlada de capas de usuario;
- preservacion de procedencia, curador, fecha, estado de revision y notas;
- generacion de reportes y exportaciones interpretables;
- lectura conservadora de faltantes, proxies y evidencia insuficiente;
- trazabilidad de campos `user_curated` por archivo y, cuando aplique, por fila.

Excluye:

- validacion clinica;
- validacion experimental definitiva;
- cambios en `scoring.py` o en la logica cientifica central;
- nuevos scores;
- comparacion exhaustiva contra literatura, que debe quedar para una fase
  posterior.

## Dataset minimo real

Un paquete minimo real o semirreal controlado debe declarar:

- `organism`;
- `strain` o alcance equivalente si la cepa no aplica;
- lista de genes o proteinas candidatas con `protein_id` y, cuando exista,
  `gene`;
- anotacion funcional minima;
- evidencia de esencialidad o relevancia, si existe;
- evidencia de conservacion, si existe;
- evidencia de selectividad, homologia con hospedero o accesibilidad, si existe;
- datos evolutivos como escape, restriccion, redundancia o compensacion, si
  existen;
- `curator_name`, `curation_date`, `review_status` o `evidence_status`;
- `source_type=user_curated`;
- `provenance`, `source_database`, `database`, referencia o notas de origen;
- `curator_notes`, `local_note` o notas equivalentes claramente marcadas como
  notas locales cuando existan.

Los campos ausentes deben quedar documentados como faltantes. La ausencia de
evidencia suficiente no equivale a bajo riesgo ni a evidencia negativa.

## Criterios de aceptacion

El dataset puede marcarse `accepted_for_test` si cumple todos estos puntos:

- pasa validacion estructural de manifest y archivos;
- conserva las columnas esperadas de identidad, procedencia y evidencia;
- no pierde `provenance`, `source_type`, curador, fecha ni notas relevantes;
- no convierte `user_curated` en `external_verified`;
- no eleva confianza por `pending_review`, `local_note`, `curator_notes` o
  `include_for_structure_check`;
- genera salidas interpretables;
- reporta datos insuficientes cuando aplique;
- mantiene separados `therapeutic_priority_score` y
  `evidence_confidence_score`;
- identifica claramente la procedencia `user_curated` en reportes y
  exportaciones.

## Criterios de fallo

El dataset debe marcarse `needs_revision` o `insufficient_evidence` si ocurre
cualquiera de estos casos:

- mezcla `user_curated` con demo, proxy, cache, online o
  `controlled_reference` como evidencia principal;
- elimina columnas criticas de identidad, procedencia o evidencia;
- asume bajo riesgo por ausencia de datos;
- convierte notas locales en DOI, literatura verificada o evidencia
  experimental;
- oculta procedencia;
- genera ranking sin advertencias cuando la evidencia es insuficiente;
- infla `evidence_confidence_score` sin soporte trazable;
- no permite distinguir prioridad terapeutica de confianza de evidencia.

## Flujo operativo sugerido

1. Crear un paquete local nuevo en `user_curated_staging/`.
2. Copiar o completar plantillas desde `data_templates/`.
3. Llenar `manifest.csv` con `source_type=user_curated`, curador,
   procedencia, estado de revision y ruta de cada archivo.
4. Colocar datos reales solo en `raw_inputs/`.
5. Validar el manifest.
6. Validar el paquete de dataset.
7. Importar una capa revisada con `--as-user-layer` cuando deba resolverse desde
   `data_user/`.
8. Ejecutar el pipeline solo en un workspace dedicado, sin `--allow-demo-data` y
   sin modo online fresco.
9. Revisar reportes, exportaciones, procedencia y advertencias.
10. Registrar la decision final: `accepted_for_test`, `needs_revision` o
    `insufficient_evidence`.

## Comandos esperados en Windows PowerShell

Crear scaffold local:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new_user_curated_dataset.ps1 -ProjectId real_user_curated_validation_01
```

Validar solo manifest:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\real_user_curated_validation_01\manifest.csv
```

Validar paquete completo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\real_user_curated_validation_01
```

Importar una capa como evidencia de usuario:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace data_sessions\real_user_curated_validation_01 --dataset essentiality --input user_curated_staging\real_user_curated_validation_01\raw_inputs\essentiality.csv --validate-user-curated-manifest user_curated_staging\real_user_curated_validation_01\manifest.csv --as-user-layer
```

Ejecutar pipeline offline despues de revision manual:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\real_user_curated_validation_01 -RunPipeline -Workspace data_sessions\real_user_curated_validation_01 -Organism "ORGANISM_NAME" -Strain "STRAIN_OR_SCOPE"
```

Pruebas especificas de esta fase:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_real_user_curated_dataset_validation_doc.py -q
```

Suite offline recomendada:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

## Resultado esperado

La fase debe producir:

- un dataset real o controlado `user_curated` preparado fuera de Git;
- reporte de validacion estructural;
- evidencia de pruebas ejecutadas;
- decision final `accepted_for_test`, `needs_revision` o
  `insufficient_evidence`;
- reportes que identifiquen procedencia `user_curated` y faltantes;
- ningun cambio en `scoring.py`;
- ningun cambio final en `config/taxon_resolution_cache.json` si solo se
  modifico por `updated_at_utc`, `saved_at_utc` o `refresh_count`.

Esta fase prepara la validacion real. No declara utilidad clinica, no valida un
tratamiento y no convierte la plataforma en predictor definitivo.

## Dataset minimo controlado 2026-05-26

Para avanzar la validacion estructural sin tocar scoring ni logica cientifica se
preparo un paquete local aislado en
`data_sessions/real_user_curated_minimal_validation_01/`.
Esa ruta es un workspace local de ejecucion y sigue ignorada por Git.

Para que las pruebas sean reproducibles en cualquier clon del repositorio,
tambien existe una copia minima versionable en
`tests/fixtures/real_user_curated_minimal_validation_01/`. El fixture conserva
solo los CSVs y notas necesarios para validar estructura, procedencia y limites
interpretativos; no es un workspace operativo y no incluye outputs pesados.

Este paquete representa:

- un dataset ficticio `user_curated` para `minimal_validation`;
- cuatro capas obligatorias: `essentiality`, `virulence`, `human_homologs` y
  `localization`;
- notas locales de curacion en `manual_curation.csv`;
- una capa `evidence_quality.csv` conservadora para preservar limites
  interpretativos;
- ausencia declarada de demo, proxy, cache, online y `controlled_reference`.

Este paquete no representa:

- validacion experimental;
- validacion clinica;
- evidencia externa verificada automaticamente;
- bajo riesgo del hospedero;
- utilidad terapeutica demostrada;
- ranking real o recomendacion clinica.

La copia en `tests/fixtures/` tampoco representa validacion experimental o
clinica. Sirve solo para que los tests no dependan de `data_sessions/`, que es
una carpeta local de ejecucion.

La validacion esperada usa los comandos actuales del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 -ManifestPath data_sessions\real_user_curated_minimal_validation_01\manifest.csv
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_dataset.ps1 -ProjectPath data_sessions\real_user_curated_minimal_validation_01
```

La importacion controlada, cuando se ejecute, debe usar `--as-user-layer` y
escribir solo dentro del mismo workspace, por ejemplo:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "Validation bacterium alpha" --strain "minimal_validation_scope_01" --workspace data_sessions\real_user_curated_minimal_validation_01 --dataset essentiality --input data_sessions\real_user_curated_minimal_validation_01\raw_inputs\essentiality.csv --validate-user-curated-manifest data_sessions\real_user_curated_minimal_validation_01\manifest.csv --as-user-layer
```

`pending_review`, `local_note`, `curator_notes` e
`include_for_structure_check` se conservan como trazabilidad. No elevan por si
solos `evidence_quality`, no equivalen a evidencia fuerte y no convierten
evidencia insuficiente en bajo riesgo.

En esta validacion local se importaron como capas de usuario las capas
soportadas por `import_dataset.py`: `essentiality`, `virulence`,
`human_homologs`, `localization` y `evidence_quality`. La importacion escribio
solo en `data_sessions/real_user_curated_minimal_validation_01/data_user/` y
conservo los CSV originales en `data_user/source_exports/`. No se ejecuto
`run_pipeline.py`, no se genero ranking y no se escribieron `results/` ni
`data_processed/` dentro del workspace.

## Interpretacion conservadora de evidencia

En el fixture portable, `evidence_quality` y `evidence_strength` se usan como
lecturas interpretativas de soporte y trazabilidad. Aunque una fila pueda llevar
`evidence_strength=strong`, esa etiqueta no significa validacion experimental
automatica, validacion clinica ni evidencia externa verificada automaticamente.
El CSV importado como capa interna conserva los campos soportados por el esquema
`evidence_quality`, mientras que el export original queda disponible en
`source_exports/` para auditar etiquetas adicionales como `evidence_strength`.

Los estados `pending_review`, `local_note`, `curator_notes` e
`include_for_structure_check` deben seguir leyendo como cautelas. No elevan
confianza por si solos, no sustituyen referencias verificadas y no convierten
`insufficient_evidence` en bajo riesgo.

Los casos negativos del fixture incluyen evidencia pendiente, insuficiente y
ausente. Esos registros deben conservarse como riesgo no resuelto o evidencia
incompleta: no son evidencia aceptada, no son `safe_target`, no demuestran bajo
riesgo y no deben presentarse como validacion biologica, experimental o clinica.
