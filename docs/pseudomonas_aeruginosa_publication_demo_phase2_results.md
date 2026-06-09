# Pseudomonas aeruginosa publication demo - Phase 2 results

## Objetivo de la Fase 2

Esta fase convierte el demo inicial de `Pseudomonas aeruginosa` en un artefacto
publicable orientado a resultados interpretables. El objetivo es documentar una
ruta reproducible desde entradas `user_curated` hasta salidas tipo manuscrito,
sin modificar la logica cientifica central de scoring ni la Teoria de Nodos
Funcionales.

La Fase 2 no cambia formulas, pesos, umbrales ni clasificaciones internas. Su
aporte es ordenar la lectura de resultados esperados, reforzar la separacion
entre prioridad terapeutica y confianza de evidencia, y dejar claro que el demo
es una demostracion reproducible de priorizacion.

## Que demuestra el demo

El demo demuestra que el repositorio puede empaquetar un caso
`user_curated` de `Pseudomonas aeruginosa` en una ruta revisable por terceros.
La ruta esta ubicada en:

```text
examples/pseudomonas_aeruginosa_publication_demo
```

El caso demuestra:

- preparacion reproducible de entradas revisables;
- conservacion de provenance y notas de curacion;
- separacion entre `therapeutic_priority_score` y
  `evidence_confidence_score`;
- uso de `evidence_strength` como lectura de soporte, no como validacion;
- exposicion de variables evolutivas como `evolutionary_escape_risk`,
  `evolutionary_constraint` y `resistance_association`;
- produccion de salidas esperadas que pueden servir como estructura de tablas
  para manuscrito;
- interpretacion conservadora de incertidumbre, datos faltantes y riesgo no
  resuelto.

## Que NO demuestra el demo

El demo no es validacion clinica. El demo no es validacion experimental.
Tampoco es un predictor clinico, una prueba de eficacia terapeutica ni una
confirmacion de seguridad. Un score alto no equivale a confianza alta, y
evidencia insuficiente no equivale a bajo riesgo.

La etiqueta `user_curated` significa que la entrada fue preparada y trazada por
el usuario o por el paquete de ejemplo. No significa que la evidencia haya sido
verificada automaticamente contra fuentes externas. La procedencia debe leerse
junto con coverage, faltantes, proxies, confidence y notas de interpretacion.

## Flujo reproducible del demo

El flujo publicable de Fase 2 mantiene el demo dentro de su propio directorio:

```text
examples/pseudomonas_aeruginosa_publication_demo/
  input/
  expected_tables/
  expected_outputs/
  run_demo.ps1
  run_demo.sh
```

Comando PowerShell:

```powershell
.\examples\pseudomonas_aeruginosa_publication_demo\run_demo.ps1
```

Comando bash:

```bash
bash examples/pseudomonas_aeruginosa_publication_demo/run_demo.sh
```

El flujo prepara un workspace local bajo el demo y evita escribir en `results/`,
`data_processed/` o `data_sessions/` globales. Cuando se use el modo dry-run, la
ejecucion debe mantenerse offline y orientada a preparacion/verificacion, no a
una afirmacion biologica final.

## Entradas usadas

Las entradas del demo estan en `examples/pseudomonas_aeruginosa_publication_demo/input`:

- `gene_list.csv`
- `manual_curation.csv`
- `evidence_quality.csv`
- `manifest.yaml`
- `provenance.yaml`
- `notes.md`

Estas entradas preservan provenance `user_curated` y mantienen banderas
explicitas para no presentar datos online, demo, proxy, cache o referencia
controlada como si fueran evidencia externa revisada.

## Salidas esperadas

Las salidas esperadas se documentan como estructuras verificables, no como
resultados inventados. La Fase 2 puede usar:

- `expected_tables/ranking_nodos.csv`
- `expected_tables/report_phase2.md`
- `expected_tables/candidate_explanations_simple.csv`
- `expected_tables/candidate_audit.csv`
- `expected_tables/evidence_strength_audit.csv`
- `expected_tables/layer_resolution_summary.csv`
- `expected_tables/publication_candidate_table.csv`
- `expected_tables/publication_interpretation_matrix.csv`
- `expected_outputs/publication_candidate_summary.csv`

Las filas finales de manuscrito deben generarse por el pipeline o por evidencia
curada y revisada. Las plantillas no deben interpretarse como resultados
experimentales.

## Tabla tipo manuscrito esperada

| gene | protein_id | functional_role | therapeutic_priority_score | evidence_confidence_score | evidence_strength | evolutionary_escape_risk | evolutionary_constraint | resistance_association | provenance | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| template_gene | template_protein_id | template_functional_role | pending_pipeline_output | pending_evidence_review | insufficient | unresolved_risk | not_assessed | not_assessed | demo_publication_template | candidate_for_reproducible_demo_only |

Esta tabla muestra el contrato de lectura. El valor de
`therapeutic_priority_score` prioriza hipotesis dentro del modelo. El valor de
`evidence_confidence_score` describe cuanta evidencia trazable sostiene la
interpretacion. Un candidato puede tener prioridad alta y confianza baja si la
evidencia depende de datos incompletos, proxies o curacion pendiente.

## Interpretacion conservadora de resultados

La lectura de Fase 2 debe seguir estas reglas:

- `therapeutic_priority_score` no debe confundirse con
  `evidence_confidence_score`.
- Un score alto no equivale a confianza alta.
- Evidencia insuficiente no equivale a bajo riesgo.
- `evidence_strength` resume soporte disponible, no valida eficacia.
- `evolutionary_escape_risk` debe permanecer visible cuando el riesgo sea
  incompleto o no resuelto.
- `provenance` debe acompanhar cada candidato para distinguir `user_curated`,
  plantilla de demo, cache, fuente externa, proxy o faltante.
- Toda interpretacion debe permanecer como priorizacion para revision, no como
  conclusion terapeutica definitiva.

## Texto reutilizable para Metodos

Se preparo un demo reproducible de `Pseudomonas aeruginosa` usando el paquete
`examples/pseudomonas_aeruginosa_publication_demo`. Las entradas se organizaron
como datos `user_curated` con manifest, provenance y notas de curacion. El demo
mantiene una ruta offline y acotada al directorio de ejemplo, preserva la
separacion entre prioridad terapeutica y confianza de evidencia, y documenta
salidas tipo manuscrito para ranking, auditoria de candidatos, fuerza de
evidencia, resolucion de capas e interpretacion conservadora.

## Texto reutilizable para Resultados

La Fase 2 produjo una estructura publicable para reportar candidatos de
`Pseudomonas aeruginosa` sin alterar el scoring central. Las tablas esperadas
incluyen campos para `therapeutic_priority_score`,
`evidence_confidence_score`, `evidence_strength`, `evolutionary_escape_risk`,
`evolutionary_constraint`, `resistance_association` y `provenance`. Esta
organizacion permite separar candidatos priorizados para revision de la fuerza
real de evidencia disponible.

## Texto reutilizable para Limitaciones

El demo debe interpretarse como una demostracion reproducible de priorizacion,
no como validacion clinica ni validacion experimental. La presencia de datos
`user_curated` no implica verificacion externa automatica. Un score alto no
equivale a confianza alta, y evidencia insuficiente no equivale a bajo riesgo.
Las variables evolutivas y de procedencia deben revisarse antes de usar
cualquier candidato como hipotesis para trabajo experimental posterior.

