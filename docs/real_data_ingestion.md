# Ingesta de datos reales

## Objetivo

La Fase 2 ya soporta tres capas opcionales que pueden alimentarse con datos
biológicos curados reales:

- `data_raw/strain_conservation.csv`
- `data_raw/functional_network.csv`
- `data_raw/host_annotation.csv`

## Regla principal

Mantén el mismo esquema tabular y sustituye el contenido de ejemplo por tus
valores curados. No es necesario cambiar el código para hacer esa transición.

## Columnas requeridas

### Conservación entre cepas

- `protein_id`
- `gene`
- `core_genome_presence`
- `strain_coverage_score`
- `allelic_conservation`
- `variant_burden`

### Red funcional

- `protein_id`
- `gene`
- `network_centrality`
- `pathway_bottleneck_score`
- `redundancy_penalty`
- `functional_dependency_score`

### Anotación de hospedero

- `protein_id`
- `gene`
- `domain_overlap_score`
- `host_criticality_penalty`

## Procedencia

La columna `database` es importante porque el pipeline la usa para auditoría de
procedencia y para ajustar parcialmente la confianza de Fase 2.

Convención recomendada:

- `curated_*` para datasets curados manualmente
- `lit_*` para datasets derivados de literatura
- `exp_*` para datasets experimentales
- `computed_*` para scores calculados computacionalmente
- `example_*` o `demo_*` solo para demostración

## Qué cambia al cargar datos reales

- `results/data_provenance_summary.csv` dejará de marcar esas capas como `demo_only`
- `optional_data_quality_score` subirá en `phase2_features.csv`
- `evidence_confidence_score` reflejará una mayor calidad de soporte opcional
- la auditoría por candidato señalará una base metodológica más fuerte

## Qué no cambia automáticamente

- El significado biológico de cada score sigue dependiendo de cómo construiste
  el dataset aguas arriba.
- Las proxies clínicas siguen siendo proxies hasta que se reemplacen por medidas
  más directas.
- La interpretación final del ranking sigue requiriendo contexto biológico.
