# Essentialidad humana para criticidad del hospedero

## Proposito cientifico

Esta fase agrega una senal auxiliar de essentialidad humana para refinar
`host_criticality_penalty` dentro de `host_annotation`. La intencion es distinguir
dos casos biologicamente diferentes:

- homologia o dominios compartidos con una proteina humana no critica
- homologia o dominios compartidos con una proteina humana esencial

La senal no crea una capa nueva del pipeline. Se usa como contexto interno de
`host_annotation` para mantener compatibilidad con los reportes y scores
existentes.

## Fuentes

Orden de uso:

1. `data_user/human_essentiality.csv`
2. `data_cache/human_essentiality.csv`
3. `data_external/human_essentiality.csv`
4. `data_raw/human_essentiality.csv`
5. proveedor opcional `biosnap_human_essentiality`

Fuente externa configurada:

- BioSNAP human essentiality dataset:
  `https://snap.stanford.edu/biodata/datasets/10033/10033-G-HumanEssential.html`
- Archivo descargable:
  `https://snap.stanford.edu/biodata/datasets/10033/files/G-HumanEssential.tsv.gz`
- Mapeo auxiliar de simbolo humano a GeneID:
  `https://clinicaltables.nlm.nih.gov/api/ncbi_genes/v3/search`

## Variables esperadas en archivo local

Un archivo local puede usar columnas como:

- `human_gene`
- `gene`
- `gene_symbol`
- `symbol`
- `entrez_gene_id`
- `gene_id`
- `human_essential`
- `essential`
- `essentiality_score`

Salida interna usada por `host_annotation`:

- `human_gene`
- `entrez_gene_id`
- `human_essential`
- `human_essentiality_score`
- `human_essentiality_lookup_status`

## Regla de scoring

Cuando InterPro tiene dominios comparables:

```text
base_criticality =
  0.75 * domain_overlap_score
  + 0.25 * human_homolog

host_criticality_penalty =
  0.80 * base_criticality
  + 0.20 * human_essentiality_score
```

Cuando InterPro no tiene dominios comparables pero hay homologia humana:

```text
base_criticality =
  0.60 * neutral_unknown_score
  + 0.40 * human_homolog

host_criticality_penalty =
  0.80 * base_criticality
  + 0.20 * human_essentiality_score
```

Si no hay homologia humana (`human_homolog=0`), la penalizacion se mantiene baja.

## Limitaciones

- La essentialidad humana depende del contexto experimental.
- BioSNAP agrega evidencia de varios entornos; no representa tejido, dosis ni
  sitio de infeccion especifico.
- Si solo existe `human_gene` curado sin GeneID, el mapeo por NCBI puede fallar
  o devolver una coincidencia no deseada.
- Esta senal aumenta cautela frente al hospedero, pero no demuestra toxicidad.

## Pasos futuros sugeridos

1. Agregar expresion por tejido o celula hospedera relevante.
2. Separar essentialidad pan-celular de dependency especifica de cancer/celula.
3. Reportar `human_essentiality_score` en el resumen de auditoria por candidato.
