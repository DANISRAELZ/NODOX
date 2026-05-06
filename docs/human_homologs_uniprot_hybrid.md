# Human homologs - proveedor UniProt hibrido

## Proposito cientifico

La capa `human_homologs` ayuda a estimar riesgo de similitud con el hospedero.
Esa senal afecta seguridad, riesgo off-target y priorizacion terapeutica.

Esta iteracion fortalece la capa sin cambiar la arquitectura del resolvedor. La
capa sigue resolviendose en este orden:

1. `data_user/human_homologs.csv`
2. `data_cache/human_homologs.csv`
3. proveedor externo `uniprot_human_gene_lookup`
4. fallback configurable

No se modifica el contrato de `layer_resolver.py`.

## Estrategia del proveedor

El proveedor `uniprot_human_gene_lookup` consulta UniProt humano con dos rutas
conservadoras:

1. busqueda por simbolo de gen bacteriano contra genes humanos
2. si no hay coincidencia por gen y existe `uniprot_annotations.csv`, busqueda
   por nombre de proteina contra proteinas humanas
3. si las rutas anteriores no encuentran coincidencia y el archivo local ya
   contiene `human_gene` curado para una fila positiva, busqueda por ese simbolo
   humano para recuperar una accesion UniProt trazable

Si la consulta real no cubre una fila, el proveedor conserva el valor del stub
configurable como backfill. Por eso el estado normal de esta fase puede ser
hibrido.

## Columnas nuevas de trazabilidad

Cuando la capa se materializa desde el proveedor externo, el CSV puede incluir:

- `homology_lookup_status`
- `homology_query_strategy`
- `homology_evidence_note`
- `human_uniprot_accession`
- `human_uniprot_id`
- `homology_evidence_tier`
- `homology_confidence_score`
- `homology_missing_flags`

Valores esperados:

- `real_match`: UniProt encontro una coincidencia humana utilizable.
- `real_partial_non_exact`: UniProt devolvio una entrada humana, pero no fue una coincidencia exacta por gen.
- `no_real_match`: UniProt no devolvio una entrada utilizable.
- `stub_backfill_after_inconclusive_real_lookup`: se conservo el stub porque la busqueda real fue inconclusa.
- `stub_only`: no hubo fila real disponible y se conservo el stub.

Estrategias esperadas:

- `human_gene_exact`
- `human_protein_name`
- `human_curated_gene`
- `configurable_stub`

## Auditoria por fila

Esta iteracion agrega una auditoria pequena y conservadora por fila. No cambia
la decision de homologia, no cambia el ranking y no reemplaza el fallback. Su
objetivo es hacer visible si una fila proviene de una coincidencia real de
UniProt, una coincidencia inconclusa o un valor retenido desde el stub.

### `homology_evidence_tier`

Clasifica la fuerza metodologica de la fila:

- `real_gene_level_match`: UniProt encontro una coincidencia por gen humano o
  por simbolo humano curado.
- `real_protein_name_match`: UniProt encontro una coincidencia por nombre de
  proteina. Es util, pero menos fuerte que una coincidencia por gen.
- `real_inconclusive_match`: UniProt devolvio una entrada humana, pero la
  coincidencia no fue exacta.
- `real_lookup_no_match`: la consulta real respondio sin encontrar una
  coincidencia utilizable.
- `stub_backfill_after_real_lookup`: se conservo el valor configurable porque
  la consulta real fue inconclusa.
- `configurable_stub_only`: la fila viene del fallback configurable sin
  evidencia real por fila.
- `legacy_or_user_supplied_unclassified`: la fila tiene valor de homologia,
  pero no trae metadatos suficientes para clasificarla con las reglas nuevas.
- `unclassified_missing_homology`: no hay informacion suficiente de homologia.

### `homology_confidence_score`

Score interpretable entre 0 y 1 que resume la calidad metodologica de la fila.
No participa en `meta_priority_score` ni en `therapeutic_priority_score` en esta
iteracion. Sirve para auditoria:

- valores altos indican coincidencia real mas trazable
- valores intermedios indican consulta real sin alineamiento o sin coincidencia
  exacta
- valores bajos indican dependencia de stub o informacion insuficiente

### `homology_missing_flags`

Lista faltantes relevantes para interpretar la fila:

- `missing_human_homolog`
- `missing_human_gene`
- `missing_alignment_evalue`
- `missing_human_uniprot_accession`

El flag `missing_alignment_evalue` es esperado en coincidencias por UniProt
REST, porque esa consulta no produce alineamientos tipo BLAST.

## Reportes nuevos

La exportacion de resultados ahora genera:

- `results/human_homologs_audit.csv`
- `results/human_homologs_audit.md`

Estos reportes agrupan candidatos por `homology_evidence_tier` y
`homology_lookup_status`, mostrando:

- numero de candidatos
- confianza media de homologia
- numero de candidatos marcados como `human_homolog=1`

La auditoria por candidato tambien conserva `human_homology_audit_summary`,
para que el riesgo de homologia humana pueda leerse junto con los scores
terapeuticos.

## Procedencia

El resolvedor mantiene las columnas de procedencia por capa:

- `human_homologs_source_type`
- `human_homologs_source_name`
- `human_homologs_is_user_supplied`
- `human_homologs_is_external`
- `human_homologs_is_cached`
- `human_homologs_is_proxy`
- `human_homologs_confidence`
- `human_homologs_retrieval_status`

Estados frecuentes:

- `api_real_partial_with_stub_backfill`: hay al menos una coincidencia real y se conserva stub para lo no resuelto.
- `api_real_inconclusive_with_stub_backfill`: la API respondio, pero no hubo coincidencias reales suficientes; se conserva stub.
- `external_real_unavailable_fallback_stub`: la consulta real fallo y se materializo el stub.

## Limitaciones actuales

- No es BLAST.
- No calcula identidad de secuencia.
- No confirma ortologia funcional.
- Una coincidencia por nombre de proteina puede ser orientativa, no definitiva.
- Una coincidencia por `human_gene` curado mejora trazabilidad hacia UniProt e
  InterPro, pero sigue dependiendo de la calidad de la curacion original.
- Si no existe `uniprot_annotations.csv`, la busqueda por nombre de proteina no se activa.
- `evalue` queda vacio para coincidencias por UniProt REST porque esta ruta no produce alineamientos.
- `homology_confidence_score` es una auditoria de calidad de evidencia, no una
  probabilidad biologica calibrada.
- Los datos de usuario antiguos siguen siendo compatibles; si no traen metadatos
  nuevos se clasifican como `legacy_or_user_supplied_unclassified`.

## Uso recomendado

Para mejorar esta capa con datos propios, colocar:

```text
data_user/human_homologs.csv
```

Ejemplo:

```csv
protein_id,gene,human_homolog,evalue,human_gene,database
PA0001,gyrB,1,1.2e-45,TOP2A,curated_user_blast
```

Para usar el modo hibrido automatico, dejar que el resolvedor llame al proveedor
configurado:

```yaml
layer_resolution:
  layers:
    human_homologs:
      strategy: user_preferred
      external_provider: uniprot_human_gene_lookup
```

## Pasos futuros sugeridos

1. Agregar una capa opcional basada en BLAST/DIAMOND si el proyecto acepta esa dependencia.
2. Guardar identidad, cobertura y e-value reales cuando exista alineamiento.
3. Separar homologos humanos directos de similitud por dominio.
4. Ajustar `host_safety_score` para distinguir evidencia real de backfill.
5. Usar `homology_confidence_score` solo como modificador de confianza, no como
   reemplazo directo de `human_homolog`, despues de revisar sensibilidad.
