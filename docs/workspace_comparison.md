# Workspace Comparison

## Propósito

`compare_workspaces.py` resume el estado de los workspaces creados en
`data_sessions/`.

## Salidas

- `results/workspace_comparison.csv`
- `results/workspace_comparison.md`

## Qué compara

- nombre del workspace
- organismo canónico
- cepa
- estado de completitud
- posibilidad de correr el pipeline
- número de datasets presentes
- número de datasets obligatorios faltantes
- top candidato y score principal si existe ranking

## Uso

```bash
python compare_workspaces.py
```

## Limitación

Es un comparador de estado y outputs, no una comparación biológica profunda
entre microorganismos.
