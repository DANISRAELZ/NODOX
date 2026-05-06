# Auditoría metodológica del scoring

## Alcance

Esta auditoría resume el estado científico-metodológico de la Fase 2 con el
pipeline actual y los datos de ejemplo incluidos en el repositorio.

## Fortalezas

- La Fase 1 se conserva como baseline explícito y comparable.
- La Fase 2 separa estrategias terapéuticas en lugar de colapsarlas en un único score.
- Los pesos viven en `config/params.yaml`, no en código duro.
- El sistema distingue mejor entre evidencia faltante, negativa y placeholder.
- La tabla de features mantiene trazabilidad de variables derivadas, proxies y placeholders.

## Hallazgos principales

### 1. `antibiotic_target_score` es actualmente la capa más robusta

Combina esencialidad, seguridad para el hospedero, conservación, factibilidad
de pequeña molécula y redundancia funcional baja. En el ejemplo actual, esta
capa empuja a candidatos tipo `murA`, `rpoB` y `ftsZ`, lo cual es coherente con
una estrategia antibiótica clásica.

### 2. `antivirulence_target_score` es útil pero depende de proxies

La señal de antivirulencia está bien separada y favorece candidatos como `lasB`
u `oprD` cuando la evidencia de virulencia y accesibilidad es alta. Sin embargo,
`host_damage_reduction_potential`, `disease_severity_association` y
`clinical_impact_score` siguen siendo aproximaciones derivadas, no medidas
clínicas directas.

### 3. `functional_node_score` ya admite datos observados, pero es sensible a la definición de red

La capa funcional deja de ser placeholder cuando existe `functional_network.csv`.
Eso endurece el ranking, pero también introduce una dependencia metodológica
fuerte: centralidad, cuello de botella y dependencia funcional no son universales
si cambian la red, el contexto biológico o el método de inferencia.

### 4. La conservación entre cepas mejora el realismo para targets antibióticos

La entrada de `strain_conservation.csv` ayuda a distinguir entre genes núcleo y
candidatos potencialmente más variables. Aun así, un dataset pequeño no sustituye
un análisis formal de pangenoma o cobertura multi-aislado.

### 5. La seguridad para el hospedero está mejor, pero todavía no completa

`host_annotation.csv` permite introducir señal más realista para
`domain_overlap_score` y `host_criticality_penalty`. El marco es correcto, pero
la calidad biológica final dependerá de la procedencia de dominios, ortología y
criticidad humana usados para alimentar esa tabla.

## Riesgos metodológicos vigentes

- Cobertura de evidencia demasiado homogénea:
  En el dataset de ejemplo, casi todos los candidatos tienen cobertura y confianza
  máximas, así que esas variables discriminan poco.
- Dependencia de proxies clínicas:
  Las variables de impacto clínico siguen siendo útiles para priorización
  exploratoria, pero no deben interpretarse como predicción clínica validada.
- Sensibilidad al diseño de pesos:
  El ranking cambia entre escenarios `baseline_like`, `antivirulence_focus` y
  `network_focus`, lo cual es esperable y sano, pero indica que la priorización
  final depende del objetivo terapéutico explícito.
- Dataset de demostración pequeño:
  Los archivos opcionales incluidos son demostrativos. Sirven para validar la
  arquitectura, no para cerrar una conclusión biológica definitiva.

## Recomendaciones

1. Alimentar `strain_conservation.csv` desde un análisis real de pangenoma o presencia/ausencia multi-cepa.
2. Documentar explícitamente cómo se construye `functional_network.csv` y qué contexto biológico representa.
3. Sustituir o complementar `host_annotation.csv` con anotaciones de dominios, ortología y esencialidad humana trazables.
4. Añadir escenarios de sensibilidad por estrategia terapéutica y no solo por meta-score.
5. Mantener los proxies clínicas etiquetadas como aproximaciones hasta disponer de datos clínicos o experimentales.

## Estado actual del repositorio

Desde esta iteración, el pipeline ya incorpora:

- resumen explícito de procedencia en `results/data_provenance_summary.csv`
- sensibilidad para `meta_priority`, `antibiotic_target`, `antivirulence_target` y `functional_node`
- auditoría por candidato en `results/candidate_audit.csv` y `results/candidate_audit.md`
- revisión priorizada del top 10 en `results/top10_candidate_review.csv` y `results/top10_candidate_review.md`

Eso no convierte automáticamente las tablas opcionales de ejemplo en evidencia real,
pero sí evita sobreinterpretarlas y deja trazable qué parte del ranking depende de
fuentes `demo`.

## Recalibración conservadora actual

Mientras la procedencia opcional siga marcada como `demo_only`, el meta-score usa una
integración ligeramente más conservadora:

- `antibiotic_target_score`: 0.50
- `antivirulence_target_score`: 0.35
- `functional_node_score`: 0.15

La idea no es declarar que la dimensión funcional sea irrelevante, sino evitar que una
capa de red todavía demostrativa domine el ranking final.
