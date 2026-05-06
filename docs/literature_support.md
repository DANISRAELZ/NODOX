# Soporte bibliografico opcional

La capa `literature_support` prepara el proyecto para curacion manual de
literatura sin cambiar los scores actuales.

## Archivo esperado

Puede colocarse en:

- `data_user/literature_support.csv`
- `data_raw/literature_support.csv`

Tambien existe una plantilla en:

- `data_templates/literature_support.csv`

Columnas:

- `protein_id`: identificador usado por el pipeline.
- `gene_id`: identificador biologico o locus tag equivalente.
- `gene`: simbolo del gen.
- `literature_support_score`: soporte curado entre 0.0 y 1.0.
- `evidence_type`: tipo de evidencia, por ejemplo `knockout`, `TnSeq`,
  `binding_assay`, `animal_model` o `pending_manual_curation`.
- `reference`: cita breve o `TO_BE_CURATED`.
- `doi_or_url`: DOI, URL o `pending_manual_curation`.
- `notes`: notas de curacion.
- `source_quality`: calidad de fuente entre 0.0 y 1.0.
- `database`: etiqueta de procedencia.

## Estado actual

La capa es interpretativa y opcional. Si no existe, el pipeline corre igual. Si
existe, se valida y normaliza, pero no modifica `meta_priority_score`,
`therapeutic_priority_score` ni ningun ranking porque
`runtime.literature_support_enabled` esta desactivado por defecto.

Cuando esta presente, el soporte bibliografico se incorpora solo en reportes:

- `results/literature_support_summary.csv`
- `results/literature_support_summary.md`
- notas interpretativas en `results/resumen_ejecutivo.md`
- columnas interpretativas en `results/top10_scientific_audit.csv`

Estas salidas indican si hubo coincidencia por `protein_id`, `gene_id` o `gene`
y repiten explicitamente que la literatura reportada no afecta el ranking.

## Ejemplo demo

`data_demo/literature_support.csv` incluye filas para `murA`, `rpoB`, `ftsZ`,
`fabI` y `lasB` marcadas como `pending_manual_curation`. No contienen
referencias especificas verificadas y no deben usarse como evidencia cientifica
final.
