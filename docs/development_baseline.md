# Development Baseline

Fecha de revisión: 2026-04-26.

Esta nota registra el estado base previo a las mejoras de madurez, trazabilidad y validación metodológica. No modifica el comportamiento del pipeline.

## Estructura revisada

Se verificó la presencia de los componentes principales del proyecto:

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

## Archivos clave

La revisión incluyó la configuración, resolución de capas, fuentes online, scoring, reporting, validación y documentación principal.

## Pruebas base

Los comandos se ejecutaron mediante el intérprete activo del entorno:

```bash
python -m pytest tests/test_validation.py -q
python -m pytest tests/test_integration.py -q
python -m pytest tests/test_scoring.py -q
```

Las tres pruebas terminaron correctamente. Se observó una advertencia de caché de pytest asociada al sistema de archivos local, sin efecto sobre los resultados.

## Demo base

Comando portable:

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

En la ejecución histórica, el pipeline alcanzó la escritura de resultados, pero encontró un `PermissionError` al sobrescribir un archivo generado previamente. La evidencia indicó un bloqueo del archivo por el entorno local, no un fallo de validación, integración o scoring.

## Interpretación

El baseline confirmó que el proyecto ya contaba con pipeline funcional, pruebas principales, auditoría inicial de procedencia, documentación científica y plantillas. El principal riesgo operativo identificado fue la interferencia de archivos bloqueados o sincronizados al sobrescribir salidas generadas.

Los workspaces y resultados deben ejecutarse en ubicaciones con permisos de escritura y fuera de carpetas sometidas a bloqueo o sincronización agresiva cuando sea necesario.
