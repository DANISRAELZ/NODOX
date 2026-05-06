# Development Baseline

Fecha de revision: 2026-04-26.

Esta nota registra el estado base antes de continuar con mejoras de madurez,
trazabilidad y validacion metodologica. No modifica el comportamiento del
pipeline.

## Estructura observada

El proyecto contiene la estructura esperada:

- `src/nodos_funcionales/`
- `tests/`
- `config/`
- `docs/`
- `data_demo/`
- `data_templates/`
- `data_raw/`
- `data_processed/`
- `results/`
- `data_sessions/`
- `scripts/`
- `run_pipeline.py`
- `requirements.txt`
- `pyproject.toml`
- `README.md`

No se detecto un directorio `.git` en la carpeta de trabajo, por lo que los
"commits" de esta fase se documentan como bloques logicos de cambios y pruebas.

## Archivos clave revisados

- `run_pipeline.py`
- `config/params.yaml`
- `src/nodos_funcionales/config.py`
- `src/nodos_funcionales/layer_resolver.py`
- `src/nodos_funcionales/online_sources.py`
- `src/nodos_funcionales/scoring.py`
- `src/nodos_funcionales/reporting.py`
- `src/nodos_funcionales/validation.py`
- `README.md`
- `docs/`
- `data_demo/`
- `data_templates/`
- `tests/`

## Pruebas base

Comandos ejecutados con:

`C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

Resultados:

- `python -m pytest tests/test_validation.py -q`: OK.
- `python -m pytest tests/test_integration.py -q`: OK.
- `python -m pytest tests/test_scoring.py -q`: OK.

Advertencia observada:

- `PytestCacheWarning` por permisos de `.pytest_cache` en OneDrive. No afecto
  el resultado de las pruebas.

## Demo base

Comando ejecutado:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Resultado:

- Discovery preparo el workspace demo.
- La resolucion taxonomica reporto `cache_hit`.
- El pipeline fallo al escribir
  `data_sessions/pseudomonas_aeruginosa_pao1/results/ranking_nodos.csv`.

Error observado:

```text
PermissionError: [Errno 13] Permission denied: '.../data_sessions/pseudomonas_aeruginosa_pao1/results/ranking_nodos.csv'
```

Interpretacion:

- El fallo parece asociado a archivo generado previamente y bloqueado o protegido
  por OneDrive/Windows.
- No se observo como fallo de validacion, integracion ni scoring.
- La fase de scripts Windows debe incluir limpieza/diagnostico de temporales y
  salidas generadas para reducir este problema.

## Estado base resumido

El proyecto ya cuenta con pipeline funcional, tests principales pasando,
auditoria de procedencia inicial, documentacion cientifica y soporte de
plantillas. El principal problema operativo observado en el baseline es la
posible interferencia de OneDrive/permisos al sobrescribir salidas generadas en
`data_sessions/`.
