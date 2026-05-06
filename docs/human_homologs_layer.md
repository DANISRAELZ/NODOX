# Human Homologs Layer

## Proposito

La capa `human_homologs` estima riesgo de similitud con hospedero. No decide
por si sola si un nodo es seguro: separa riesgo biologico de calidad de
evidencia.

## Niveles de evidencia

- Nivel 0: `missing`, sin datos.
- Nivel 1: `configurable_stub_human_homologs_v1`, solo respaldo controlado.
- Nivel 2: `user_curated_human_homologs.csv`, curacion manual.
- Nivel 3: `external_real_homology_lookup`, lookup real parcial.
- Nivel 4: `reproducible_sequence_similarity_pipeline`, archivo local de
  ortologia o similitud reproducible.

## Plantilla

Usar `data_templates/human_homologs_template.csv`. Columnas principales:

- `protein_id`, `gene`
- `human_hit_id`, `human_hit_name`
- `percent_identity`, `query_coverage`, `subject_coverage`
- `evalue`, `bit_score`, `shared_domain_count`
- `orthology_method`, `source_database`, `evidence_source_type`
- `curator_notes`

## Interpretacion

`unknown` significa que no hay datos suficientes para evaluar homologia humana.
No debe leerse como bajo riesgo.

`low_host_similarity_risk` solo debe usarse cuando existe evidencia real o
curada de ausencia de homologia significativa.

`high_host_similarity_risk` penaliza seguridad cuando hay identidad, cobertura,
dominios compartidos o curacion positiva trazable.
