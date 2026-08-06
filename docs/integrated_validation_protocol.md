# Fase integrada de validación biológica y computacional

## Alcance de Stage 1

Stage 1 prepara la validación sin cambiar fórmulas, pesos, umbrales, rankings históricos ni valores predeterminados de proveedores. Su función es producir un inventario reproducible del estado del repositorio y una matriz que conecte la Teoría de Nodos Funcionales con código, evidencia y salidas observables.

## Objetivo científico

La contribución principal es la Teoría de Nodos Funcionales. NODOX es su operacionalización computacional y las corridas por organismo son pruebas de concepto. La fase separa explícitamente:

- prioridad terapéutica;
- confianza y cobertura de evidencia;
- riesgo de escape evolutivo;
- restricción del espacio evolutivo;
- estados de incertidumbre y procedencia.

## Reglas no negociables

1. `missing_input`, `insufficient_evidence`, `unresolved` y fallos de proveedor no son evidencia negativa.
2. Un no-hit de DIAMOND no demuestra seguridad frente al hospedero.
3. Recuperación técnica no equivale a evidencia utilizable ni a efecto sobre el score.
4. Datos demo, fixtures y proxies no son evidencia experimental.
5. Los puntajes no son probabilidades.
6. Stage 1 no modifica scoring ni pesos.
7. Toda afirmación del manuscrito debe poder rastrearse a un archivo y a un commit.

## Productos del auditor

El comando:

```bash
python scripts/audit_integrated_validation.py \
  --repo-root . \
  --output-dir results/integrated_validation_stage1
```

genera:

- `repository_state.json`;
- `available_runs_inventory.csv`;
- `provider_coverage_matrix.csv`;
- `evidence_source_inventory.csv`;
- `functional_node_postulates_matrix.csv`;
- `evolutionary_escape_variables.csv`;
- `manuscript_supported_claims.csv`;
- `manuscript_unsupported_claims.csv`;
- `integrated_validation_readiness_report.md`.

## Criterio de salida

Stage 1 concluye cuando:

- se conoce el SHA real de `main` y el estado del árbol;
- se identifica la corrida reproducible principal;
- se distinguen proveedores recuperados, mapeados, utilizables y con efecto real;
- los seis postulados tienen estado explícito;
- las variables evolutivas están clasificadas como implementadas, observadas, derivadas, proxy o ausentes;
- existe una lista de afirmaciones defendibles y otra de afirmaciones no respaldadas;
- se propone el alcance del siguiente PR sin alterar todavía el modelo.

## Ejecución de pruebas

```bash
python -m pytest -q \
  tests/test_integrated_validation_audit.py \
  tests/test_postulate_coverage_matrix.py
```
