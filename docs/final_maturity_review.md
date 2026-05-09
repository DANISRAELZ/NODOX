# Revision final de madurez

Fecha: 2026-04-26.

Esta revision resume los bloques logicos de trabajo realizados para fortalecer
Nodos Funcionales como herramienta de priorizacion computacional exploratoria.
No se modificaron formulas de scoring, pesos ni contrato publico de
`run_pipeline.py`.

## 1. Archivos creados

- `docs/development_baseline.md`
- `docs/cpseudotuberculosis_data_integration_plan.md`
- `docs/evidence_strength_framework.md`
- `docs/windows_execution_guide.md`
- `docs/biological_validation_framework.md`
- `docs/biological_validation_summary_template.md`
- `docs/final_maturity_review.md`
- `data_templates/*.csv`
- `docs/generic_annotation_import.md`
- `docs/online_organism_enrichment.md`
- `docs/project_boundaries.md`
- `data_templates/biological_validation_targets.csv`
- `scripts/run_tests.ps1`
- `scripts/run_demo.ps1`
- `scripts/run_cpseudo_dryrun.ps1`
- `scripts/clean_project.ps1`
- `tests/test_generic_organism_templates.py`
- `tests/test_evidence_strength_audit.py`
- `tests/test_windows_scripts_exist.py`
- `tests/test_biological_validation_templates.py`

Archivos de auditoria de procedencia existentes y verificados:

- `docs/layer_source_audit.md`
- `docs/layer_source_audit.json`
- `docs/layer_source_summary.csv`
- `tests/test_layer_source_audit.py`

## 2. Archivos modificados

- `README.md`
- `src/nodos_funcionales/reporting.py`
- `scripts/clean_project.ps1`
- `tests/test_layer_source_audit.py`

## 3. Cambios por punto critico

### Auditoria real de procedencia por capa

Se verifico y reforzo la auditoria de:

- `essentiality`
- `virulence`
- `human_homologs`
- `localization`
- `strain_conservation`
- `functional_network`
- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`
- `host_annotation`
- `literature_support`

Cada capa tiene etiquetas, fuente primaria/secundaria, soporte de cache, demo,
proxy/controlado, riesgo cientifico y `evidence_priority_level`.

### Ejemplo multi-organismo para C. pseudotuberculosis

Se creo estructura de ejemplo para `Corynebacterium pseudotuberculosis`:

- `data_templates/`
- `templates/`
- `metadata/`

Las plantillas estan vacias salvo encabezados para evitar datos biologicos
inventados. El ejemplo no representa una coleccion particular de aislados ni
un proyecto genomico independiente.

### Separacion entre evidencia fuerte y debil

Se agrego un reporte interpretativo:

- `results/evidence_strength_audit.csv`
- `results/evidence_strength_audit.md`

Clasifica evidencia como:

- `strong`
- `moderate`
- `weak`
- `insufficient`

No altera `meta_priority_score`, `therapeutic_priority_score` ni
`ranking_nodos.csv`.

### Instalacion y ejecucion en Windows

Se agregaron scripts PowerShell:

- `scripts/run_tests.ps1`
- `scripts/run_demo.ps1`
- `scripts/run_cpseudo_dryrun.ps1`
- `scripts/clean_project.ps1`

Los scripts resuelven `PYTHON_EXE`, `python`, `py` o el interprete local
conocido. La guia Windows documenta uso, limpieza y problemas con OneDrive.

### Validacion biologica

Se agrego marco de validacion biologica:

- `docs/biological_validation_framework.md`
- `docs/biological_validation_summary_template.md`
- `data_templates/biological_validation_targets.csv`

La plantilla permite curar evidencia, degradar candidatos y planear validacion
experimental sin declarar eficacia terapeutica.

## 4. Niveles de prioridad de evidencia

- `essentiality`: `2_external_real_traceable`
- `virulence`: `2_external_real_traceable`
- `human_homologs`: `6_proxy_or_controlled`
- `localization`: `2_external_real_traceable`
- `strain_conservation`: `2_external_real_traceable`
- `functional_network`: `2_external_real_traceable`
- `clinical_impact`: `6_proxy_or_controlled`
- `curated_disease_context`: `6_proxy_or_controlled`
- `therapy_site_context`: `6_proxy_or_controlled`
- `host_annotation`: `4_raw_local`
- `literature_support`: `8_missing_or_template_only`

## 5. Pruebas ejecutadas

Todas pasaron:

- `tests/test_validation.py -q`
- `tests/test_integration.py -q`
- `tests/test_scoring.py -q`
- `tests/test_layer_source_audit.py -q`
- `tests/test_generic_organism_templates.py -q`
- `tests/test_evidence_strength_audit.py -q`
- `tests/test_windows_scripts_exist.py -q`
- `tests/test_biological_validation_templates.py -q`

Advertencia recurrente:

- `PytestCacheWarning` por permisos de `.pytest_cache` en OneDrive. No afecto
  los resultados de pruebas.

## 6. Resultado de corrida demo

Comando exacto solicitado:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Resultado:

- Discovery y manifests se generaron.
- Fallo al sobrescribir
  `data_sessions/pseudomonas_aeruginosa_pao1/results/ranking_nodos.csv` por
  `PermissionError`.
- La causa probable es archivo generado bloqueado por OneDrive o un proceso
  externo.

Control adicional:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --workspace data_sessions\pao1_maturity_verify
```

Resultado: OK. El pipeline ejecuto con 53 filas de validacion, 10 nodos
integrados, 10 features y 10 scores.

## 7. Resultado dry-run C. pseudotuberculosis

Comando:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --acquisition-mode semi_auto --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --dry-run
```

Resultado: OK. El dry-run preparo discovery, reporte y manifest, sin ejecutar
scoring.

## 8. Limpieza

Se ejecuto `scripts/clean_project.ps1`.

Estado:

- `__pycache__`: no detectado.
- `*.pyc`: no detectado.
- `.pip_tmp`: no detectado.
- `.tmp_tests`: no detectado.
- `pytest-cache-files-*`: no detectado.
- `.pytest_cache`: persiste como directorio por permisos/OneDrive aunque se
  intento borrar directamente.

No se eliminaron `data_user`, `data_templates`, `docs`, `src`, `tests` ni
`data_demo`.

## 9. Pendientes tecnicos

- Resolver bloqueo/permisos de `.pytest_cache` en OneDrive.
- Resolver bloqueo del ranking generado en
  `data_sessions/pseudomonas_aeruginosa_pao1/results/`.
- Considerar corrida de demo en workspace nuevo o limpieza manual de salidas
  generadas antes de empaquetar.
- Si se desea, mejorar escritura de reportes con diagnostico mas claro cuando
  un archivo de salida esta bloqueado.

## 10. Pendientes cientificos

- Cargar datos reales del usuario cuando se quiera una corrida curada para `C. pseudotuberculosis`.
- Sustituir stubs o backfills de homologia por ortologia reproducible.
- Curar evidencia para impacto clinico, contexto de infeccion y sitio
  terapeutico.
- Curar literatura con DOI/URL verificables.
- Separar evidencia experimental, inferida, proxy y demo en cualquier reporte
  cientifico.

## 11. Recomendaciones para la siguiente fase

1. Llenar primero un workspace de usuario con datos curados y trazables.
2. Ejecutar una corrida real en un workspace nuevo, evitando archivos bloqueados
   de OneDrive.
3. Revisar `evidence_strength_audit.csv` junto con `ranking_nodos.csv`.
4. Completar `biological_validation_targets.csv` para el top 10.
5. Solo despues considerar cambios opcionales de scoring, desactivados por
   defecto y comparados contra el baseline.
