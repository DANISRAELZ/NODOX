# NODOX — parche Stage 1 de validación integrada

Este paquete añade exclusivamente infraestructura de auditoría y preparación. No cambia scoring, pesos, proveedores, rankings ni resultados históricos.

## Aplicación local

Desde la raíz del repositorio NODOX:

```bash
git switch main
git pull --ff-only origin main
git status --short

git switch -c feat/integrated-validation-stage1
unzip -o /ruta/nodox_integrated_validation_stage1.zip -d .

python -m pytest -q \
  tests/test_integrated_validation_audit.py \
  tests/test_postulate_coverage_matrix.py

python scripts/audit_integrated_validation.py \
  --repo-root . \
  --output-dir results/integrated_validation_stage1 \
  --fail-on-dirty
```

Nota: `--fail-on-dirty` debe ejecutarse antes de aplicar cambios adicionales. Como el propio parche deja archivos nuevos sin commit, para generar la auditoría después de aplicarlo puede omitirse temporalmente o hacerse el primer commit del parche antes de ejecutar el auditor.

## Flujo recomendado

```bash
git add config docs scripts tests README_STAGE1_PATCH.md
git diff --cached --check
git commit -m "Add integrated validation readiness audit"

python scripts/audit_integrated_validation.py \
  --repo-root . \
  --output-dir results/integrated_validation_stage1

git status -sb
```

Los resultados generados no deben fusionarse automáticamente. Primero deben revisarse para seleccionar la corrida principal y definir el alcance de Stage 2.
