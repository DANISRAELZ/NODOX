# Alineacion de proveedores externos por capa

## Proposito

Esta fase consolida la arquitectura de resolucion por capa para que el registro
base, la configuracion principal y la documentacion describan el mismo estado
del pipeline.

El objetivo cientifico es mantener la trazabilidad de cada senal usada para
priorizar nodos funcionales sin saltarse el resolvedor existente.

## Capas alineadas

El registro base ahora declara como proveedores externos por defecto:

- `essentiality`: `deg_real`
- `virulence`: `vfdb_real`
- `human_homologs`: `human_homology_diamond` como proveedor primario; `uniprot_human_gene_lookup` queda solo como evidencia auxiliar no concluyente.
- `localization`: `uniprot_real`
- `host_annotation`: `interpro_domain_overlap`
- `strain_conservation`: `bvbrc_real`
- `functional_network`: `string_real`
- `clinical_impact`: `controlled_therapeutic_context_v2`
- `curated_disease_context`: `controlled_therapeutic_context_v2`
- `therapy_site_context`: `controlled_therapeutic_context_v2`

La configuracion por capa en `config/params.yaml` sigue teniendo prioridad
sobre estos valores. Esto conserva compatibilidad con estrategias como
`user_preferred`, `external_preferred` y `merge_with_priority`.

## Reglas preservadas

- Si existe `data_user/<layer>.csv` y la capa usa `user_preferred`, el pipeline
  no consulta innecesariamente el proveedor externo.
- Si existe cache valida, se puede usar antes de consultar la fuente externa
  segun la estrategia configurada.
- Toda capa resuelta conserva columnas de procedencia:
  `<layer>_source_type`, `<layer>_source_name`,
  `<layer>_is_user_supplied`, `<layer>_is_external`,
  `<layer>_is_cached`, `<layer>_is_proxy`, `<layer>_confidence` y
  `<layer>_retrieval_status`.
- `workspace_stub` sigue disponible solo como compatibilidad para
  configuraciones antiguas o archivos ya materializados en `data_external/`.

## Limitaciones actuales

- `human_homologs` puede consumir una tabla local de ortologia reproducible y,
  si no existe, sigue usando el lookup parcial en UniProt humano por simbolo de
  gen o nombre de proteina. El pipeline no ejecuta ortologia por secuencia.
- Las capas terapeuticas controladas son interpretables y reproducibles, pero no
  reemplazan curacion experimental o clinica.
- La ausencia de una coincidencia en una fuente externa no equivale a ausencia
  biologica; debe interpretarse como evidencia incompleta.

## Paso futuro sugerido

El siguiente avance cientifico mas fuerte es mejorar la produccion y auditoria
de la tabla local de ortologia:

1. agregar un template de `data_external/human_homologs_orthology.csv`;
2. documentar parametros recomendados para BLAST, DIAMOND, HMMER u OrthoFinder;
3. reportar resumen por `orthology_method`;
4. combinar evidencia local, curacion manual y lookup UniProt por prioridad de
   fila.
