# Organism Workflow

## Resumen

El flujo es multiorganismo: cada organismo/cepa/análisis debe vivir en un
workspace independiente. Los workspaces existentes usan `data_raw/`,
`data_processed/`, `results/` y `config/`; una evolucion futura puede exponer
aliases `input/`, `processed/`, `audit/`, `reports/`, `cache/`, `manifest.json`
y `organism_config.yaml` sin romper la estructura actual.

1. El usuario invoca `run_pipeline.py --organism ...`
2. Se resuelve el nombre del microorganismo
3. Se crea un workspace en `data_sessions/<slug>/`
4. Se clasifican datasets obligatorios, opcionales y futuros
5. Se genera un manifest de adquisición
6. Si hay datos suficientes, corre el motor existente
7. Si no, el sistema deja un reporte claro de faltantes

## Artefactos clave

- `results/organism_profile.json`
- `results/acquisition_manifest.json`
- `results/discovery_report.md`

## Criterio de corrida

El pipeline puede correr si:

- los datasets obligatorios están presentes y son utilizables
- no hay restricciones de procedencia incompatibles con la política pedida

## Demo empaquetado y casos de validacion

El repositorio incluye un demo local para `Pseudomonas aeruginosa` `PAO1` y
casos de validacion/documentacion con otros organismos. Son ejemplos de uso, no
el nucleo biologico del sistema.

Solo se usa cuando:

- el organismo coincide
- se activa `--allow-demo-data`

Eso se marca explícitamente como `demo` y no como dato real curado.
