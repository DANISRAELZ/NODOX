# Fase de estabilidad, trazabilidad y robustez operativa

## Proposito

Esta fase endurece el proyecto sin cambiar su contrato historico. Mantiene Fase 1 legacy y Fase 2 modular, pero separa mejor pruebas, scoring, reportes para usuarios no tecnicos, modos online y mensajes de error en Windows/OneDrive.

## Cambios principales

- `scoring_components.py` concentra calculos testeables de score legacy, scores por estrategia, meta-prioridad y seleccion de estrategia preferida.
- `user_explanations.py` genera explicaciones simples por candidato sin afirmar evidencia externa cuando solo hay demo, proxy, cache o datos incompletos.
- `online/online_utils.py` explicita los modos `offline_only`, `local`, `cache_first`, `online_optional`, `auto` y `api_stub`.
- `online/provenance.py` agrega campos de procedencia operativa: `source_version`, `retrieval_mode`, `cache_status` y `provenance`.
- `tests/conftest.py` garantiza marcadores pytest operativos para separar suites offline, online, lentas e integracion.

## Compatibilidad preservada

Se conservan los archivos principales:

- `results/ranking_nodos_legacy.csv`
- `legacy_score_final`
- `data_processed/phase2_features.csv`
- `data_processed/scored_nodes.csv`
- `results/ranking_nodos.csv`
- `results/phase_comparison.csv`
- `results/sensitivity_analysis.csv`
- `results/report_phase2.md`
- `results/top10_scientific_audit.*`

Los nuevos reportes son adicionales:

- `results/candidate_explanations_simple.csv`
- `results/candidate_explanations_simple.md`

## Evidencia ausente vs evidencia negativa

La ausencia de evidencia se trata como `missing` o `no_evidence`: reduce confianza, pero no penaliza como evidencia biologica negativa. La evidencia negativa requiere una fuente trazable no demo/no proxy, por ejemplo homologia humana real o una senal curada adversa.

## Modos online

- `offline_only` y `local`: no abren red; usan cache/datos locales o fallan trazablemente.
- `cache_first`: intenta cache antes de cualquier consulta.
- `online_optional`: puede consultar red y debe degradar a cache, stub o missing si falla.
- `auto`: alias conservador de `cache_first`.
- `api_stub`: no abre red; sirve para validar contratos sin usar APIs reales.

## Windows/OneDrive

Los errores de lectura/escritura deben indicar acciones concretas: cerrar Excel, esperar sincronizacion, mantener archivos locales, revisar permisos o mover el workspace fuera de OneDrive.

## Pasos futuros

- Mover gradualmente mas bloques de `scoring.py` a helpers pequenos cuando haya pruebas de equivalencia por ranking.
- Dividir `online_sources.py` por familias de proveedores cuando los contratos de capa esten completamente cubiertos por pruebas.
- Agregar snapshots de ranking para comparar cambios numericos esperados en datasets controlados.
