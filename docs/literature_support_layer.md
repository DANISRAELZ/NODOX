# Literature Support Layer

## Proposito

`literature_support` permite incorporar literatura curada como evidencia real.
No sube el score terapeutico por menciones genericas: requiere relevancia
funcional, terapeutica, de seguridad, resistencia o escape.

## Plantilla

Usar `data_templates/literature_support_template.csv` con:

- `protein_id`, `gene`, `organism`, `disease_context`
- `evidence_type`
- `therapeutic_relevance`, `virulence_relevance`, `essentiality_relevance`
- `resistance_relevance`, `host_safety_relevance`,
  `evolutionary_escape_relevance`
- `citation`, `doi`, `pubmed_id`, `year`
- `evidence_strength`, `evidence_source_type`, `curator_notes`

## Reglas

- Literatura curada con DOI/PubMed o cita clara eleva `evidence_quality_score`.
- Relevancia positiva en esencialidad, virulencia o explotabilidad terapeutica
  fortalece la interpretacion.
- Relevancia negativa en seguridad, resistencia o escape penaliza.
- Una plantilla vacia se reporta como `missing_or_template_only`.

## Ejemplos curados empaquetados

El repositorio incluye una primera semilla offline en
`data_external/curated_catalogs/literature_support/pseudomonas_aeruginosa_pao1.csv`.
Ese archivo fue curado a partir de entradas PubMed/NCBI para genes de PAO1 como
`ftsZ`, `oprD`, `lasB` y `pvdA`. Durante la resolucion de capas, el proveedor
`curated_online_examples` materializa estas filas en el workspace como
`data_external/literature_support.csv` y conserva `pubmed_id`, `doi`,
`citation`, `catalog_protein_id` y `curated_online_match_status`.

Estos ejemplos no sustituyen la curacion del usuario ni pretenden ser una base
exhaustiva. Son evidencia real curada de arranque: elevan la calidad de evidencia
solo para los candidatos que coinciden por `protein_id` o por simbolo de gen, y
mantienen separados los efectos positivos y negativos.
