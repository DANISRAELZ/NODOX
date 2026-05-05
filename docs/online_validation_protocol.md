# Protocolo de validacion online controlada

## Objetivo

Validar conectores externos reales sin volver obligatoria la red para la suite offline. Las pruebas online deben estar marcadas con `online` y no ejecutarse con `-m "not online"`.

## Modos esperados

- `offline_only`: no abre red; requiere cache/datos locales o falla trazablemente.
- `local`: alias de `offline_only`; no abre red.
- `api_stub`: alias de `offline_only`; no abre red.
- `cache_first`: usa cache antes de red.
- `auto`: alias conservador de `cache_first`.
- `online_optional`: unico modo que permite red; si falla debe degradar a cache, stub o missing cuando el conector lo permita.

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
