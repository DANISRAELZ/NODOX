# User-curated conservation transformation

## Proposito

Esta fase implementa una transformacion minima, aislada y controlada de una
tabla local `user_curated` de conservacion hacia la forma esperada por
`strain_conservation`.

La funcion agregada es pura: lee un CSV, valida columnas criticas y devuelve un
`pandas.DataFrame`. No escribe archivos, no importa capas, no ejecuta scoring,
no ejecuta `run_pipeline.py`, no usa modo online y no genera ranking
terapeutico.

## Por que hace falta

`raw_inputs/conservation.csv` no se importaba directamente porque
`conservation` no es un dataset interno aceptado por `import_dataset.py`.
El destino minimo controlado es `strain_conservation` porque conserva las
variables principales de conservacion usadas por el pipeline:

- `protein_id`;
- `gene`;
- `core_genome_presence`;
- `strain_coverage_score`;
- `allelic_conservation`;
- `variant_burden`;
- `database`.

## Funcion disponible

```python
transform_user_curated_conservation_to_strain_conservation(input_path)
```

La funcion vive en:

```text
src/nodos_funcionales/user_curated_transformations.py
```

Devuelve un `DataFrame` con las columnas exactas de
`data_templates/strain_conservation_template.csv`.

## Campos preservados

La salida mantiene columnas directas cuando la plantilla lo permite:

- `protein_id`;
- `gene`;
- `core_genome_presence`;
- `strain_coverage_score`;
- `allelic_conservation`;
- `variant_burden`.

Como la plantilla `strain_conservation` no tiene columnas propias para
`organism`, `strain`, `conservation_scope`, `source_type`, `evidence_status` o
`curator_notes`, esos metadatos se preservan dentro de `database` como una
cadena auditable:

```text
source_database=...; source_type=user_curated; organism=...; strain=...; conservation_scope=...; evidence_status=...; curator_notes=...
```

Esta decision conserva trazabilidad sin inventar columnas fuera de la plantilla.

## Reglas conservadoras

- No inventar scores.
- No rellenar valores faltantes como `0`.
- No convertir `unknown` en `low`.
- No convertir `false` en bajo riesgo evolutivo.
- No asumir que `core_genome_presence=true` equivale a alta prioridad
  terapeutica.
- No asumir que `strain_coverage_score` bajo equivale a baja relevancia.
- No asumir que `conservation.csv` es `redundancy`.
- No modificar `therapeutic_priority_score`.
- No modificar `evidence_confidence_score`.
- No ejecutar scoring.
- No ejecutar `run_pipeline.py`.

La funcion puede normalizar `core_genome_presence=true` a `1` y
`core_genome_presence=false` a `0` para ajustarse al esquema de
`strain_conservation`, pero esos valores siguen siendo presencia observada, no
lectura de riesgo, prioridad o certeza clinica.

## Limites

Esta transformacion no equivale a evidencia clinica. Tampoco convierte
conservacion en prioridad terapeutica. La salida debe revisarse antes de usarse
en una corrida real.

`user_curated` sigue separado de `demo`, `proxy`, `cache` y
`controlled_reference`. La ausencia de evidencia no significa bajo riesgo.

`therapeutic_priority_score` y `evidence_confidence_score` siguen separados. La
transformacion no calcula ninguno de los dos.

## Validacion esperada

La prueba asociada cubre:

- transformacion exitosa con CSV temporal;
- preservacion de `gene`, `protein_id`, `organism` y `strain`;
- preservacion de `source_database`, `evidence_status` y `curator_notes` dentro
  de trazabilidad equivalente;
- conservacion de incertidumbre y `unknown` sin convertirlos en bajo riesgo;
- ausencia de scores inventados;
- columnas exactas compatibles con `strain_conservation_template.csv`;
- error claro cuando faltan columnas criticas;
- ausencia de escritura en workspaces locales;
- ausencia de defaults de PAO1, H37Rv o Corynebacterium;
- orientacion multi-organismo.

## Estado de cierre

Estado: transformacion minima disponible como funcion pura y testeada. La
siguiente fase puede decidir si exportar el resultado a un workspace dedicado,
pero solo con una funcion explicita de escritura, revision de procedencia y sin
ejecutar scoring durante la importacion.
