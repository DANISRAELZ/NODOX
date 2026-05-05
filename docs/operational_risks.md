# Riesgos operativos

## Riesgos actuales

- `online_sources.py` aparece no rastreado en este workspace.
- APIs externas pueden cambiar contratos, limites, campos o disponibilidad.
- Cache obsoleto puede parecer evidencia actual si no se revisa `cache_status` y fecha.
- Diferencias de punto flotante pueden aparecer aunque no cambie la formula.
- OneDrive o Excel pueden bloquear lectura/escritura de CSV y reportes.
- Datos demo, proxy o stub pueden confundirse con evidencia real si no se revisa procedencia.
- Snapshots no curados pueden congelar un estado incorrecto del ranking.

## Mitigaciones implementadas

- Modos online normalizados en `online/online_utils.py` y `online/provider_modes.py`.
- Procedencia estandarizada con `source_name`, `source_version`, `retrieval_mode`, `cache_status`, `provenance` y `confidence`.
- Tests offline que verifican que cache/local/offline no abren red para STRING y UniProt.
- Separacion explicita entre evidencia ausente y evidencia negativa.
- Mensajes de error para OneDrive/Excel con acciones concretas.
- `ranking_snapshot.csv` y referencia curada PAO1 para detectar regresiones.
- `candidate_explanations_simple.*` advierte sobre demo/proxy/cache y confianza.

## Mitigaciones pendientes

- Versionar `online_sources.py` completo o dividirlo bajo control de versiones.
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
