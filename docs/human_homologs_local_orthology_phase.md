# Human Homologs Local Orthology Phase

## Proposito cientifico

Esta fase permite complementar el proveedor parcial de UniProt para
`human_homologs` con un archivo local de ortologia reproducible. El objetivo es
reducir dependencia del backfill configurable sin introducir consultas online
obligatorias ni cambiar el contrato del resolvedor por capas.

## Entrada nueva

El proveedor `uniprot_human_gene_lookup` revisa primero:

```text
data_external/human_homologs_orthology.csv
```

Si el archivo existe, se materializa como `data_external/human_homologs.csv` y
se reporta con:

- `source_name`: `local_reproducible_orthology`
- `retrieval_status`: `local_orthology_file_materialized`
- `confidence`: `online_sources.human_homologs_lookup.confidence_local_orthology`

No se consulta UniProt cuando esta entrada local esta disponible.

## Columnas esperadas

Columnas minimas:

- `protein_id`
- `gene`
- `human_gene`
- `human_homolog`
- `evalue`

Columnas recomendadas de trazabilidad:

- `orthology_method`
- `orthology_tool`
- `orthology_version`
- `orthology_reference`
- `orthology_query_coverage`
- `orthology_subject_coverage`
- `orthology_percent_identity`
- `orthology_bitscore`
- `orthology_confidence_score`
- `orthology_evidence_note`

## Reglas de mapeo

- Si `human_homolog=1`, se conserva como homologo humano positivo.
- Si falta `human_homolog`, se acepta como positivo solo cuando
  `orthology_confidence_score` alcanza `local_orthology_min_confidence` y existe
  `human_gene`.
- Si no hay soporte suficiente, se marca `human_homolog=0` y
  `homology_lookup_status=local_orthology_no_match`.
- Las filas positivas reciben `homology_evidence_tier=local_reproducible_orthology`.

## Limitaciones actuales

- El pipeline no ejecuta BLAST, DIAMOND, HMMER ni OrthoFinder; solo consume un
  resultado local ya generado.
- La calidad biologica depende del metodo externo usado para producir el CSV.
- La ausencia de fila local no significa ausencia de homologia; solo evidencia
  no aportada.

## Pasos futuros sugeridos

1. Agregar un template especifico para `human_homologs_orthology.csv`.
2. Documentar perfiles recomendados para DIAMOND o BLAST reciprocal best hit.
3. Reportar resumen separado de evidencia por `orthology_method`.
4. Permitir combinar ortologia local y lookup UniProt por prioridad de fila.
