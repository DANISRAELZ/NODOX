# Riesgos operativos

## Riesgos actuales

- `online_sources.py` esta rastreado y sigue siendo un contrato operativo grande; el riesgo actual es migrarlo sin pruebas de equivalencia.
- Bug operativo documentado el 04/05/2026: `--taxon-resolution-mode offline_only`
  bloqueaba la resolucion taxonomica online, pero no impedia que proveedores de
  capas externas intentaran red desde `online_sources.py`.
- APIs externas pueden cambiar contratos, limites, campos o disponibilidad.
- Cache obsoleto puede parecer evidencia actual si no se revisa `cache_status` y fecha.
- Diferencias de punto flotante pueden aparecer aunque no cambie la formula.
- OneDrive o Excel pueden bloquear lectura/escritura de CSV y reportes.
- Datos demo, proxy o stub pueden confundirse con evidencia real si no se revisa procedencia.
- Snapshots no curados pueden congelar un estado incorrecto del ranking.

## Mitigaciones implementadas

- Modos online normalizados en `online/online_utils.py` y `online/provider_modes.py`.
- `run_pipeline.py` acepta `--online-source-mode` y fuerza modo offline seguro para
  fuentes externas cuando se usa `--offline-only`, `--taxon-resolution-mode offline_only`,
  `local` o `api_stub`.
- `fetch_layer_external_source()` actua como cortafuegos central antes de proveedores
  reales: en `offline_only`, `local` y `api_stub` no llama UniProt, STRING, DEG, VFDB,
  BV-BRC, InterPro ni ningun `urllib.request.urlopen`.
- Procedencia estandarizada con `source_name`, `source_version`, `retrieval_mode`, `cache_status`, `provenance` y `confidence`.
- Tests offline que verifican que cache/local/offline no abren red para STRING y UniProt.
- Tests offline especificos para `human_homologs` con `uniprot_human_gene_lookup`.
- Separacion explicita entre evidencia ausente y evidencia negativa.
- Mensajes de error para OneDrive/Excel con acciones concretas.
- `ranking_snapshot.csv` y referencia curada PAO1 para detectar regresiones.
- `candidate_explanations_simple.*` advierte sobre demo/proxy/cache y confianza.

## Mitigaciones pendientes

- Dividir `online_sources.py` en modulos especializados solo con pruebas de equivalencia y fachada compatible.
- Ejecutar validacion online manual en una red estable y guardar manifiestos.
- Definir politica de expiracion/renovacion de cache por proveedor.
- Crear snapshots curados para un organismo real no demo.
- Agregar revision humana obligatoria antes de actualizar snapshots de referencia.

## Recomendaciones para usuarios no tecnicos

- No interpretar datos `demo`, `proxy`, `stub`, `cache` o `missing` como evidencia biologica real.
- Revisar `candidate_explanations_simple.md` antes de leer tablas grandes.
- Cerrar Excel antes de ejecutar el pipeline.
- Si el workspace esta en OneDrive, esperar sincronizacion o copiarlo a una carpeta local.
- Usar snapshots solo como control de estabilidad, no como prueba cientifica.

## Recomendaciones para desarrolladores

- Mantener pruebas offline como barrera obligatoria antes de cambios.
- No cambiar formulas de scoring sin snapshot, justificacion y documentacion.
- Versionar cambios grandes en proveedores en commits separados.
- Preservar nombres de columnas historicas.
- Mantener cada fuente externa detras del resolvedor por capa y con procedencia explicita.
