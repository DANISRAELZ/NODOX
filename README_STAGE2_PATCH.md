# NODOX integrated validation — Stage 2

Este parche añade una auditoría específica de la corrida v10g y una ablación reproducible del componente evolutivo.

No modifica producción, pesos, defaults, proveedores ni resultados históricos.

## Ejecución

```bash
python scripts/audit_selected_run.py \
  --repo-root . \
  --run-dir results/20260805_helicobacter_pylori_online_strict_25_v10g_final_audit \
  --output-dir results/integrated_validation_stage2/v10g_audit

python scripts/run_evolutionary_ablation.py \
  --repo-root . \
  --run-dir results/20260805_helicobacter_pylori_online_strict_25_v10g_final_audit \
  --output-dir results/integrated_validation_stage2/v10g_ablation
```

## Pruebas

```bash
python -m pytest -q \
  tests/test_selected_run_audit.py \
  tests/test_evolutionary_ablation.py
```
