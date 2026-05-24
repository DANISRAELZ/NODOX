# User-curated minimal layer compatibility map

## Proposito

Este documento mapea los archivos locales del paquete minimo `user_curated`
contra los datasets internos aceptados por `import_dataset.py`, sin importar
nuevas capas. La regla central es conservadora: no se deben forzar archivos
locales a datasets internos incompatibles solo porque exista un CSV.

Paquete local de referencia:

```text
user_curated_staging/minimal_user_curated_validation_01/
```

Ese paquete permanece local e ignorado por Git. `user_curated_staging/` no debe
versionarse.

## Datasets internos aceptados

`import_dataset.py --help` mostro que los datasets internos aceptados son:

```text
clinical_impact, collateral_sensitivity, contextual_essentiality,
curated_disease_context, essentiality, evidence_quality, evolutionary_escape,
evolutionary_escape_risk, functional_network, host_annotation, human_homologs,
literature_support, localization, redundancy, strain_conservation,
therapy_site_context, virulence.
```

`gene_list` no esta entre datasets internos aceptados.

## Mapa de compatibilidad

| Archivo local | Corresponde directamente a dataset interno aceptado | Dataset interno sugerido | Estado | Motivo | Precauciones |
| --- | --- | --- | --- | --- | --- |
| `raw_inputs/evolutionary_escape_risk.csv` | Si | `evolutionary_escape_risk` | `already_validated` | Ya fue importado como primera capa `user_curated` usando `--as-user-layer`; el dataset interno existe en `import_dataset.py`. | Mantener como subcapa evolutiva interpretativa; `evolutionary_escape_risk` es modulador de riesgo, no certeza clinica. |
| `raw_inputs/gene_list.csv` | No | Ninguno directo | `not_importable_as_dataset` | `gene_list` no aparece en `import_dataset.py --help`. | Usar como inventario de candidatos o insumo previo; no es capa interna de scoring por si sola. |
| `raw_inputs/manual_curation.csv` | No | Conceptualmente podria informar `literature_support`, `evidence_quality` o notas interpretativas | `requires_mapping` | La curacion manual no tiene dataset interno directo con ese nombre. | No forzar sin especificacion; debe conservarse como evidencia revisada o curada, no como score automatico. |
| `raw_inputs/functional_annotations.csv` | No | Conceptualmente podria informar `functional_network`, `contextual_essentiality`, `literature_support` o anotacion auxiliar | `requires_mapping` | `functional_annotations` no aparece como dataset interno aceptado con ese nombre. | No importar sin mapeo formal; anotacion funcional no equivale a evidencia experimental directa. |
| `raw_inputs/conservation.csv` | No | Conceptualmente podria informar `strain_conservation` o `redundancy` | `requires_mapping` | `conservation` no aparece como dataset interno aceptado con ese nombre. | No asumir automaticamente que `conservation.csv` equivale a `strain_conservation`; requiere transformacion explicita segun columnas y semantica. |

## Reglas de importacion futura

- Cada capa requiere mapeo explicito antes de importarse.
- No debe forzarse una importacion solo porque exista un CSV local.
- No se debe mapear `conservation.csv` automaticamente a
  `strain_conservation` sin transformacion explicita.
- `manual_curation.csv` debe conservarse como evidencia revisada o curada, no
  como score automatico.
- `functional_annotations.csv` puede orientar interpretacion o mapeos futuros,
  pero anotacion funcional no equivale a evidencia experimental directa.
- `gene_list.csv` puede funcionar como inventario de candidatos o insumo
  previo, no como capa interna de scoring por si sola.

## Separacion de procedencia

`user_curated` no equivale a `demo`, `proxy`, `cache` ni
`controlled_reference`. El mapa preserva esa separacion: una fila local curada
puede ser trazable, pero no debe mezclarse con fuentes demo, proxies, cache o
referencias controladas como si fueran equivalentes.

Evidencia insuficiente no significa bajo riesgo. Los faltantes o campos no
mapeados deben leerse como incertidumbre o riesgo no resuelto hasta que exista
curacion adicional.

`therapeutic_priority_score` y `evidence_confidence_score` siguen separados.
Este mapa no calcula scores y no debe mezclar prioridad terapeutica con
confianza de evidencia.

`evolutionary_escape_risk` es modulador interpretativo, no certeza clinica.

## Garantias de esta fase

Esta fase es solo documentacion y prueba de contrato:

- no se ejecutara scoring;
- no se ejecutara pipeline;
- no se ejecutara `run_pipeline.py`;
- no se ejecutara modo online;
- no se generara ranking terapeutico;
- no se modificara `src/nodos_funcionales/scoring.py`;
- no se modificara `run_pipeline.py`;
- no se modificaran snapshots;
- no se modificara `results/`;
- no se modificara `data_processed/`;
- no se modificara `data_sessions/`;
- no se modificara `config/taxon_resolution_cache.json`;
- no se versionara `user_curated_staging/`.

## Paso futuro sugerido

Antes de importar nuevas capas del paquete minimo, definir una especificacion
por archivo con columnas de entrada, dataset interno destino, transformacion,
campos retenidos, campos descartados y advertencias de procedencia. Solo despues
de esa especificacion debe ejecutarse una nueva importacion controlada.
