# Protocolo de validacion online controlada

## Objetivo

Validar conectores externos reales sin volver obligatoria la red para la suite offline. Las pruebas online deben estar marcadas con `online` y no ejecutarse con `-m "not online"`.

La fase de congelamiento posterior al cierre limpio del 2026-05-06 no debe ejecutar validacion fresh contra STRING ni UniProt. Su alcance es auditar contratos, documentar puntos de corte y reforzar pruebas offline.

## Modos esperados

- `offline_only`: no abre red; requiere cache/datos locales o falla trazablemente.
- `local`: alias de `offline_only`; no abre red.
- `api_stub`: alias de `offline_only`; no abre red.
- `cache_first`: usa cache antes de red.
- `auto`: alias conservador de `cache_first`.
- `online_optional`: unico modo que permite red; si falla debe degradar a cache, stub o missing cuando el conector lo permita.

## Taxonomia vs fuentes externas

`taxon_resolution_mode` controla solo como se resuelve el organismo y su `taxon_id`.
`online_source_mode` controla si las capas externas pueden abrir red.

Para ejecuciones completamente offline, `--offline-only`, `--taxon-resolution-mode offline_only`,
`--taxon-resolution-mode local` y `--taxon-resolution-mode api_stub` fuerzan
`online_source_mode=offline_only` durante la ejecucion del pipeline. Esto evita que
capas como `human_homologs`, `functional_network`, `localization`, `host_annotation`,
`essentiality`, `virulence` o `strain_conservation` llamen proveedores reales.

El argumento compatible para controlar fuentes externas es:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --online-source-mode online_optional
```

## Comandos recomendados

Ejecucion completamente offline/cache segura:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

PAO1 demo reproducible sin red:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

Validacion online controlada:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode cache_first --online-source-mode online_optional
```

## Interpretacion de procedencia

- `api_real_success` o `api_real`: evidencia externa real recuperada durante una llamada permitida.
- `cache_hit`: dato servido desde cache local; no implica actualidad.
- `cache_miss_offline_mode` o `api_not_requested_offline_mode`: no se abrio red por modo offline seguro.
- `stub` o `configurable_stub`: relleno trazable para conservar el contrato; no es evidencia real.
- `proxy`: valor por defecto explicito para mantener compatibilidad; no es evidencia real.
- `missing` o `absence`: ausencia de dato, no evidencia biologica negativa.

## Comandos manuales PowerShell

Auditoria controlada STRING/UniProt en workspace separado:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode online_optional --force-refresh --disable-cache-read --compare
```

STRING directo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe fetch_online_data.py --source string --organism "Pseudomonas aeruginosa" --taxon-id 208964 --mode online_optional
```

UniProt directo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe fetch_online_data.py --source uniprot --organism "Pseudomonas aeruginosa" --taxon-id 208964 --mode online_optional
```

Variantes de modo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode offline_only --compare
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode cache_first --compare
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode api_stub --compare
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode auto --compare
```

Suite online:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m online -q
```

## Informacion que debe registrarse

Cada validacion online debe revisar manifiestos o reportes y registrar:

- fecha/hora de consulta;
- `source_version` cuando exista;
- `retrieval_mode`;
- `cache_status`;
- numero de entradas recuperadas;
- numero de entradas faltantes;
- fallos de red;
- degradacion a cache, stub o missing.

## Criterios de aceptacion

- `offline_only`, `local` y `api_stub` no deben llamar red.
- `cache_first` debe servir cache si existe antes de intentar red.
- `online_optional` puede llamar red, pero debe registrar fallos y fallback.
- Si una API cambia o falla, el pipeline no debe presentar cache/stub/missing como evidencia externa real.
- Durante fases de documentacion o congelamiento, cualquier comando `online_optional` debe quedar como protocolo escrito, no ejecutado, salvo instruccion explicita de validacion online.

## Evidencia y procedencia obligatoria

Los manifiestos o resultados de conectores deben conservar:

- `source_name`
- `source_version`
- `retrieval_mode`
- `cache_status`
- `provenance`
- `confidence`
- `query_id` o `protein_id` cuando aplique;
- timestamp o fecha de consulta cuando sea online real;
- `error_status` si fallo;
- `fallback_used` si degrado.

Si el dato es incompleto, la confianza debe quedar limitada y la procedencia debe indicar la degradacion.

## Escenarios de validacion

### Escenario 1. `offline_only`

- No debe abrir red.
- Debe usar cache/datos locales o marcar `missing`/`no_evidence`.
- Debe registrar `retrieval_mode=offline_only`.
- Si no hay cache, debe fallar con mensaje trazable o degradar segun contrato del conector.

### Escenario 2. `cache_first`

- Debe intentar cache antes de red.
- Si hay cache valida, debe registrar `cache_status=cache_hit`.
- Si no hay cache y la configuracion permite red, puede consultar de forma controlada.
- Debe conservar `provenance`.

### Escenario 3. `online_optional`

- Puede abrir red.
- Debe consultar STRING/UniProt si estan configurados.
- Si falla red/API, debe degradar a cache, stub o missing cuando el modo lo permita.
- Debe registrar fallo y fallback sin afirmar evidencia externa real.

### Escenario 4. `api_stub`

- No debe abrir red.
- Debe validar contratos de salida.
- Debe marcar evidencia como stub/cache/missing, nunca como `real_external_evidence`.

### Escenario 5. `auto`

- Debe actuar como alias conservador de `cache_first`.
