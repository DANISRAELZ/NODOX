# Host annotation externa controlada

## Proposito cientifico

Esta fase incorpora `host_annotation` al resolvedor por capas sin cambiar el
contrato de `layer_resolver.py`. La capa estima riesgo potencial para el
hospedero a partir de dominios InterPro cuando hay accesiones UniProt
comparables. Si faltan esas accesiones o no hay dominios comparables, conserva
un fallback controlado desde la capa `human_homologs` ya resuelta.

El objetivo es hacer explicita una senal que el scoring ya usaba como fallback:
si una proteina bacteriana comparte dominios con una proteina humana, o tiene
homologia humana sin dominios comparables, aumenta el riesgo de solapamiento
funcional o de efecto fuera de objetivo. Esta fase no afirma evidencia
experimental nueva.

## Variables nuevas o materializadas

La salida sigue el contrato existente de `host_annotation.csv`:

- `protein_id`
- `gene`
- `domain_overlap_score`
- `host_criticality_penalty`
- `database`

Tambien se agregan columnas de trazabilidad interpretables:

- `interpro_bacterial_accession`
- `interpro_human_accession`
- `interpro_bacterial_entries`
- `interpro_human_entries`
- `interpro_shared_entries`
- `human_essentiality_score`
- `human_essentiality_status`
- `interpro_rule`
- `interpro_missing_flags`
- `host_annotation_rule`
- `host_annotation_inputs`
- `host_annotation_confidence_reason`
- `host_annotation_missing_flags`

Estas columnas se propagan a `data_processed/integrated_nodes.csv` y
`data_processed/phase2_features.csv` cuando existen. Los reportes exportan un
resumen compacto en `host_risk_audit_summary` para revisar, por candidato, si el
riesgo al hospedero proviene de dominios InterPro comparables, de essentialidad
humana auxiliar o de fallback controlado.

La auditoria cientifica del top 10 tambien conserva `host_risk_audit_summary` y
genera `host_risk_interpretation`, una frase legible que resume nivel de riesgo,
fuente, estado de recuperacion y faltantes sin modificar ningun score.

## Reglas de scoring

Proveedor primario: `interpro_domain_overlap`.

Fuente:

- InterPro API: `https://www.ebi.ac.uk/interpro/api`
- Endpoint usado: `/entry/interpro/protein/uniprot/{accession}/`

Entrada principal:

- `uniprot_accession` desde `uniprot_annotations.csv`
- `human_uniprot_accession` desde `human_homologs.csv`, cuando el lookup
  humano real o la busqueda por `human_gene` curado la aporta
- `human_homolog`
- `human_essentiality_score`, si existe en cache, archivo local o fuente externa

Reglas InterPro:

- si hay dominios bacterianos y humanos comparables, `domain_overlap_score` es
  la fraccion de entradas InterPro compartidas sobre la union de entradas.
- `host_criticality_penalty` combina el solapamiento de dominios, la senal de
  homologia humana y la essentialidad humana cuando esta disponible.
- si `human_homolog=0`, el solapamiento y la penalizacion se mantienen bajos.
- si faltan accesiones o dominios comparables, se marca la incompletitud en
  `interpro_missing_flags`.

Formula InterPro:

```text
domain_overlap_score =
  shared_interpro_entries / union_interpro_entries

host_criticality_penalty =
  0.80 * (0.75 * domain_overlap_score + 0.25 * human_homolog)
  + 0.20 * human_essentiality_score
```

Proveedor de respaldo: `controlled_host_annotation_v1`.

Entrada principal:

- `human_homolog`
- `evalue`
- `homology_lookup_status`, si existe

Reglas:

- `human_homolog=0` produce similitud humana baja.
- `human_homolog=1` con `evalue` significativo aumenta la similitud humana.
- si falta `evalue`, se usa un valor explicito moderado (`0.60`) y se marca
  `default_evalue_missing`.
- coincidencias reales de UniProt aumentan `domain_overlap_score`.
- resultados inconclusos aumentan moderadamente `host_criticality_penalty`,
  porque se tratan como riesgo no resuelto, no como evidencia segura.

Formulas:

```text
domain_overlap_score =
  0.70 * human_similarity
  + 0.20 * human_homolog
  + 0.10 * real_match_signal

host_criticality_penalty =
  0.60 * human_similarity
  + 0.25 * human_homolog
  + 0.15 * inconclusive_signal
```

Ambos scores se recortan al rango `[0, 1]`.

## Procedencia

El resolvedor conserva la prioridad configurada:

1. `data_user/host_annotation.csv`
2. `data_cache/host_annotation.csv`
3. `data_external/host_annotation.csv`
4. `data_raw/host_annotation.csv`
5. proveedor `interpro_domain_overlap`, solo si no hay datos previos
6. fallback `controlled_host_annotation_v1`, solo si InterPro no aporta pares de
   dominios comparables

Cuando el proveedor materializa la capa, el manifest registra:

- `host_annotation_source_type=external`
- `host_annotation_source_name=interpro_api` cuando hay pares de dominios
  comparables
- `host_annotation_source_name=interpro_api+controlled_host_annotation_v1` cuando
  cae al fallback controlado
- `host_annotation_is_external=True`
- `host_annotation_confidence=0.72` para InterPro comparable
- `host_annotation_confidence=0.56` para fallback controlado desde el proveedor
  InterPro
- `host_annotation_retrieval_status=api_real` o
  `interpro_no_comparable_domains_fallback_controlled`

## Limitaciones actuales

- InterPro describe familias, dominios y sitios funcionales; no mide toxicidad.
- La comparacion requiere accesiones UniProt bacterianas y humanas trazables.
- La essentialidad humana viene de una fuente agregada o archivo local; no
  representa necesariamente el tejido o contexto de infeccion relevante.
- No usa expresion por tejido.
- No demuestra toxicidad en hospedero; solo estima riesgo de similitud.
- Si `human_homologs` proviene de fallback, la calidad cientifica de esta capa
  tambien queda limitada.

## Pasos futuros sugeridos

1. Separar riesgo por mecanismo terapeutico: molecula pequena, anticuerpo,
   inhibidor extracelular o estrategia antivirulencia.
2. Agregar expresion por tejido o contexto celular del hospedero para separar
   riesgo teorico general de riesgo relevante en el sitio de infeccion.
