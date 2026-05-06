# Proveedores externos reales - Fase 2

## Proposito

Esta fase conecta tres capas biologicas criticas al resolvedor externo existente,
sin cambiar el contrato de `layer_resolver.py`:

- `essentiality` mediante DEG.
- `virulence` mediante VFDB.
- `strain_conservation` mediante BV-BRC / PATRIC.
- `host_annotation` mediante InterPro, con fallback controlado derivado de
  `human_homologs`.
- criticidad humana auxiliar mediante BioSNAP/NCBI para modular
  `host_criticality_penalty`.

Las fuentes se invocan solo detras de `fetch_layer_external_source()`. Si el
resolvedor encuentra datos de usuario, cache o `data_raw/` segun la estrategia
de cada capa, mantiene esa prioridad y no consulta la fuente externa.

## DEG para essentiality

Fuente:

- URL: `https://tubic.org/deg/public/index.php`
- Tipo de acceso: busqueda HTTP simple. DEG no expone una API JSON formal
  estable, por lo que el proveedor acepta respuestas JSON o TSV/texto cuando
  existan.

Salida:

- `protein_id`
- `gene`
- `essential`
- `evidence`
- `database`

Campos observados:

- coincidencias por `protein_id`, `locus_tag`, `gene` o campos equivalentes.
- evidencia experimental si la respuesta la incluye (`evidence`, `experiment`,
  `method`).

Campos derivados:

- `essential=1` si el candidato aparece en DEG.
- `essential=0` y `evidence=not_in_deg` si la consulta fue exitosa pero el
  candidato no aparece.

Limitacion:

- ausencia en DEG no prueba no esencialidad; solo indica que no se observo en la
  respuesta consultada.

## VFDB para virulence

Fuente:

- URL: `http://www.mgc.ac.cn/VFs/Down`
- Tipo de acceso: descarga HTTP de archivo curado, preferentemente
  `VFs.tsv.gz`. El proveedor tambien acepta payload JSON en pruebas o si una
  descarga futura expone datos estructurados.

Salida:

- `protein_id`
- `gene`
- `virulence_score`
- `virulence_factor`
- `database`

Campos observados:

- coincidencias por `protein_id`, `locus_tag`, `gene` o identificadores
  equivalentes.
- categoria funcional cuando existe (`category`, `vfcategory`, `function`).

Campos derivados:

- `virulence_factor=1` si el candidato aparece en VFDB.
- `virulence_score` se deriva de la categoria del factor cuando existe:
  toxinas, secrecion, adhesinas o invasion reciben soporte alto; regulacion,
  biofilm o motilidad reciben soporte intermedio-alto.
- `virulence_factor=0` y `virulence_score=0.0` si la consulta fue exitosa pero
  no hay coincidencia.

Limitacion:

- el score es interpretable y heuristico; no reemplaza una lectura curada del
  mecanismo de virulencia.

## BV-BRC para strain_conservation

Fuente:

- URL: `https://www.bv-brc.org/api/`
- Tipo de acceso: REST JSON.
- Endpoint usado: `/genome_feature/` con filtros por `taxon_lineage_ids` y
  `feature_type=CDS`.

Salida:

- `protein_id`
- `gene`
- `core_genome_presence`
- `strain_coverage_score`
- `allelic_conservation`
- `variant_burden`
- `database`

Campos observados:

- `patric_id`
- `gene`
- `pgfam_id`
- `figfam_id`
- `genome_id`

Campos derivados:

- `core_genome_presence`: fraccion de genomas consultados donde aparece el gen.
- `strain_coverage_score`: igual a la presencia normalizada en esta primera
  version.
- `allelic_conservation`: se mantiene en `0.50` cuando no hay datos suficientes
  de variantes o familias multiples.
- `variant_burden`: se mantiene en `0.50` cuando no hay datos suficientes de
  variantes.

Limitacion:

- esta version no consulta SNPs ni variantes finas. Cuando no hay datos de
  variantes, el manifest incluye una nota indicando defaults explicitos.

## InterPro para host_annotation

Fuente:

- URL: `https://www.ebi.ac.uk/interpro/api`
- Documentacion: `https://interpro-documentation.readthedocs.io/en/latest/download.html`
- Endpoint usado: `/entry/interpro/protein/uniprot/{accession}/`

Salida:

- `protein_id`
- `gene`
- `domain_overlap_score`
- `host_criticality_penalty`
- `database`
- columnas de trazabilidad `interpro_*`

Campos observados:

- accesion UniProt bacteriana desde `uniprot_annotations.csv`
- accesion UniProt humana desde `human_homologs.csv`, cuando el lookup humano
  real la aporta
- entradas InterPro asociadas a cada accesion UniProt

Campos derivados:

- `domain_overlap_score`: fraccion de entradas InterPro compartidas entre la
  proteina bacteriana y su contraparte humana sobre la union de entradas.
- `host_criticality_penalty`: combinacion interpretable de solapamiento de
  dominios y senal de homologia humana.

Limitacion:

- InterPro no mide toxicidad ni esencialidad humana. Cuando no existen
  accesiones comparables, el proveedor marca la incompletitud y cae a
  `controlled_host_annotation_v1`.

## BioSNAP / NCBI para essentialidad humana

Fuente:

- BioSNAP human essentiality:
  `https://snap.stanford.edu/biodata/datasets/10033/10033-G-HumanEssential.html`
- Archivo descargable:
  `https://snap.stanford.edu/biodata/datasets/10033/files/G-HumanEssential.tsv.gz`
- NCBI Clinical Tables Gene API:
  `https://clinicaltables.nlm.nih.gov/api/ncbi_genes/v3/search`

Uso:

- No crea una capa nueva del pipeline.
- Se usa como contexto auxiliar dentro de `interpro_domain_overlap`.
- Puede reemplazarse por archivos locales `human_essentiality.csv` en
  `data_user/`, `data_cache/`, `data_external/` o `data_raw/`.

Salida interna:

- `human_essentiality_score`
- `human_essentiality_status`

Limitacion:

- la essentialidad humana es dependiente del contexto experimental; se interpreta
  como penalizacion conservadora de seguridad, no como toxicidad demostrada.

## Cache y modos

Cada proveedor usa cache JSON en `config/`:

- `deg_essentiality_cache.json`
- `vfdb_virulence_cache.json`
- `bvbrc_conservation_cache.json`
- `interpro_host_annotation_cache.json`
- `human_essentiality_cache.json`

La estructura base es:

```json
{"schema_version": 1, "updated_at_utc": null, "entries": {}}
```

Modos:

- `offline_only`: usa solo cache y falla si no hay entrada compatible.
- `cache_first`: usa cache si existe; si no, intenta API.
- `online_optional`: intenta API; si falla y hay cache, cae a cache.

Si la API falla y no hay cache, el proveedor no inventa evidencia: devuelve una
tabla vacia, `api_success=false` y notas de error en el manifest. El resolvedor
puede entonces continuar con sus fallbacks actuales.

## Refresh de cache

Las funciones publicas aceptan:

- `refresh_cache=True` para ignorar una entrada previa y consultar otra vez.
- `no_write_cache=True` para evitar escribir el resultado.

Esto es equivalente al patron usado por los flujos de auditoria online con
`--force-refresh`: se fuerza una recuperacion nueva, pero el pipeline sigue
siendo reproducible porque la respuesta queda trazada en cache y manifest salvo
que se indique `no_write_cache`.

## Procedencia

Cuando una capa se resuelve desde estos proveedores, el manifest registra:

- proveedor
- modo
- taxon id
- cantidad de proteinas consultadas
- cantidad de coincidencias
- `source_used`
- `api_success`
- notas y errores

El resolvedor conserva la procedencia de capa en
`results/layer_resolution_manifest.json`. Las capas incluidas en
`TARGET_LAYER_KEYS`, incluyendo `strain_conservation` y `host_annotation`, tambien
se propagan a `integrated_nodes.csv` con columnas `<layer>_source_type`,
`<layer>_source_name`, `<layer>_confidence` y estado de recuperacion.

## Pasos futuros

1. Confirmar endpoints descargables estables de DEG y VFDB por organismo.
2. Agregar parsers especificos si las fuentes publican formatos oficiales nuevos.
3. Incorporar variantes BV-BRC cuando exista un endpoint estable para SNPs por
   grupo de cepas.
4. Conectar dominios compartidos o criticidad humana real para fortalecer
   `host_annotation`, manteniendo el proveedor controlado como fallback
   reproducible.
