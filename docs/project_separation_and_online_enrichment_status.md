# Estado de separacion y enriquecimiento online

Fecha: 2026-05-08

Nota de estado: este documento conserva el cierre historico de la fase de
separacion y enriquecimiento online. El estado de release actual ya supero el
bloqueo local descrito abajo: la suite offline `not online` fue restaurada y
pasa al 100% en el entorno `.venv` del repositorio.

## Referencias eliminadas o renombradas

- `src/nodos_funcionales/cpseudo_import.py` fue renombrado a `src/nodos_funcionales/generic_annotation_import.py`.
- `tests/test_cpseudo_import.py` fue renombrado a `tests/test_generic_annotation_import.py`.
- `tests/fixtures/cpseudo_annotations/` fue movido a `tests/fixtures/generic_organism_annotations/`.
- Los documentos `docs/cpseudo_mexico_real_data_audit.md`, `docs/cpseudo_mexico_real_data_import.md` y `docs/cpseudo_mexico_import_status.md` fueron eliminados y reemplazados por documentacion generica.

## Referencias conservadas

- El snapshot `data_external/curated_snapshots/corynebacterium_pseudotuberculosis_biovar_ovis/` se conserva como snapshot controlado generico multi-organismo. Debe seguir indicando que no es evidencia fresca ni datos de una coleccion particular.
- Las sesiones en `data_sessions/` estan ignoradas por git. No se usan como documentacion operativa ni como evidencia del proyecto.

## Riesgos evitados

- No se eliminaron conectores existentes.
- No se cambio el contrato del resolvedor por capa.
- No se reemplazaron proveedores reales por stubs.
- Los fixtures quedaron bajo `tests/fixtures/` y se tratan solo como datos de prueba.

## Consulta online organism-first

Se agrego `src/nodos_funcionales/online_organism_enrichment.py` y se extendio `fetch_online_data.py` con `--sources`.

Ejemplo:

```powershell
python fetch_online_data.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions/corynebacterium_pseudotuberculosis_online_demo --sources uniprot string --mode online_optional --force-refresh
```

El flujo:

1. Resuelve taxonomia.
2. Consulta UniProt para crear `candidate_universe.csv`.
3. Deriva `localization.csv` desde UniProt cuando hay evidencia.
4. Genera proxies de virulencia solo desde anotacion, marcados como `inferred_proxy`.
5. Intenta STRING para `functional_network.csv`.
6. Escribe reporte y auditoria online.

## Validacion ejecutada

- `py_compile` para `import_dataset.py`, `fetch_online_data.py`, `generic_annotation_import.py` y `online_organism_enrichment.py`: OK.
- `tests/test_generic_annotation_import.py tests/test_online_organism_enrichment.py tests/test_generic_organism_templates.py tests/test_windows_scripts_exist.py`: OK, 20 pruebas.
- Busqueda de referencias operativas a `cpseudo_mexico`, `Mexican isolates`, `aislados mexicanos`, `17 isolates` y `pangenome mexicano`: solo quedan menciones justificadas en `docs/project_separation_audit.md`, este estado y el test que verifica ausencia en docs operativos.
- Ejemplo `cache_first`:

```powershell
python fetch_online_data.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --sources uniprot string --mode cache_first
```

Resultado: OK, taxon id `1719`, reportes generados, capas vacias marcadas como `missing_input` o `insufficient_evidence`.

- Ejemplo `online_optional --force-refresh`: bloqueado por el runtime local con `OPENSSL_Uplink ... no OPENSSL_Applink` antes de que la excepcion pueda manejarse en Python. Se repitio con permisos escalados y el resultado fue el mismo.
- Corrida del pipeline sobre el workspace generico: OK informativo; no ejecuta ranking porque faltan capas obligatorias con filas reales.

En esta fase historica, la suite offline completa habia quedado pendiente por
el mismo bloqueo OpenSSL observado previamente en pruebas existentes del
resolvedor online. Ese pendiente ya no representa el estado actual del proyecto:
la suite offline `not online` pasa al 100% en el entorno local preparado para
release.

## Limitaciones

- El flujo online general no sustituye datos locales del usuario.
- Sin datos locales, algunas capas obligatorias para ranking completo pueden seguir incompletas.
- `evolutionary_escape_risk.csv` usa `unknown` o `insufficient_evidence` cuando no hay pangenoma, variantes, HGT, movilidad o resistoma.

## Estado de git final de esta fase historica

La rama de trabajo es `codex-project-separation-online-enrichment`.

Cambios previos no relacionados siguen presentes en `.gitignore`, snapshots PAO1, documentacion multi-organismo previa, `src/nodos_funcionales/curated_snapshots.py` y `tests/test_curated_snapshots.py`.

Cambios de esta iteracion:

- `README.md`
- `fetch_online_data.py`
- `import_dataset.py`
- `scripts/run_cpseudo_dryrun.ps1`
- `src/nodos_funcionales/generic_annotation_import.py`
- `src/nodos_funcionales/online_organism_enrichment.py`
- `tests/test_generic_annotation_import.py`
- `tests/test_online_organism_enrichment.py`
- `tests/fixtures/generic_organism_annotations/`
- `docs/generic_annotation_import.md`
- `docs/online_organism_enrichment.md`
- `docs/project_boundaries.md`
- `docs/project_separation_audit.md`
- `docs/project_separation_and_online_enrichment_status.md`
- limpieza de docs operativos que referian el workspace anterior.
