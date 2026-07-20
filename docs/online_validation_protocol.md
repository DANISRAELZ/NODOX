# Protocolo de validación online controlada

## Objetivo

Validar conectores externos reales sin volver obligatoria la red para la suite offline. Las pruebas online deben estar marcadas con `online` y ejecutarse por separado.

## Modos esperados

- `offline_only`: no abre red; usa datos locales o cache y registra faltantes.
- `local`: alias de `offline_only`.
- `api_stub`: valida contratos sin abrir red.
- `cache_first`: intenta cache antes de red.
- `auto`: alias conservador de `cache_first`.
- `online_optional`: único modo que permite red; debe registrar errores y fallback.

`taxon_resolution_mode` controla la resolución del organismo y su `taxon_id`. `online_source_mode` controla si las capas externas pueden abrir red.

## Ejecuciones recomendadas

Completamente offline:

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

Validación online controlada:

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode cache_first --online-source-mode online_optional
```

Los organismos anteriores son ejemplos reproducibles. Para otro organismo, sustituya `--organism` y `--strain` y mantenga el modo de red adecuado.

## Auditoría por fuente

```bash
python audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions/pao1_online_validation --sources string uniprot --mode online_optional --force-refresh --disable-cache-read --compare
```

Consulta directa de STRING:

```bash
python fetch_online_data.py --source string --organism "Pseudomonas aeruginosa" --taxon-id 208964 --mode online_optional
```

Consulta directa de UniProt:

```bash
python fetch_online_data.py --source uniprot --organism "Pseudomonas aeruginosa" --taxon-id 208964 --mode online_optional
```

Suite online:

```bash
python -m pytest -p no:cacheprovider -m "online and not organism_regression" -q
```

## Interpretación de procedencia

- `api_real_success` o `api_real`: respuesta externa recuperada durante una llamada permitida.
- `cache_hit`: respuesta reutilizada; no implica actualidad.
- `cache_miss_offline_mode` o `api_not_requested_offline_mode`: no se abrió red.
- `stub`: salida controlada para validar el contrato; no es evidencia real.
- `proxy`: aproximación explícita; reduce confianza.
- `missing`: ausencia de dato, no evidencia biológica negativa.

## Información obligatoria

Cada validación debe registrar:

- fecha y hora;
- proveedor y versión cuando exista;
- modo de recuperación;
- estado de cache;
- registros recuperados y faltantes;
- errores de red o API;
- fallback utilizado;
- identificadores de consulta;
- confianza y limitaciones.

## Criterios de aceptación

- Los modos offline no deben abrir red.
- `cache_first` debe preferir cache válido.
- `online_optional` puede consultar proveedores, pero debe registrar fallos y degradación.
- Cache, stub, proxy o missing nunca deben presentarse como respuesta externa fresca.
- Las pruebas deterministas de contrato deben usar respuestas controladas.
- Las comprobaciones de disponibilidad real deben ser diagnósticas y tener timeout individual.

## Escenarios mínimos

1. `offline_only`: datos locales/cache o faltantes trazables.
2. `cache_first`: reutilización antes de red.
3. `online_optional`: llamada real con fallback explícito.
4. `api_stub`: contrato sin red.
5. `auto`: comportamiento conservador equivalente a `cache_first`.
