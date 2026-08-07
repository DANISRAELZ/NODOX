# Stage 4A — contrato de evidencia evolutiva explícita

## Propósito

Stage 4A define cuándo una observación puede alimentar la salida evolutiva
respaldada de NODOX. No consulta todavía proveedores, no cambia los pesos, no
modifica el score proxy y no altera corridas históricas.

## Registro mínimo

Cada observación debe conservar:

- candidato y gen;
- variable evolutiva;
- valor normalizado entre 0 y 1;
- tipo, base, registro y versión de la fuente;
- fecha de recuperación;
- método y estado de mapeo;
- estado de la evidencia;
- confianza;
- grupo de independencia;
- alcance del método cuando el resultado sea `not_detected_with_method`.

## Regla de evidencia explícita

Una observación sólo es explícita cuando simultáneamente:

1. la variable pertenece al contrato;
2. el valor es finito y está entre 0 y 1;
3. la fuente pertenece a una clase explícita reconocida;
4. la procedencia obligatoria está completa;
5. el mapeo es directo al candidato;
6. el estado es `observed` o `not_detected_with_method`;
7. el registro solicita `is_explicit=true`;
8. el validador no encuentra errores.

El validador puede rechazar `is_explicit=true`. La bandera del proveedor no
tiene autoridad por sí sola.

## Ausencia de evidencia

Los estados `missing_input`, `insufficient_evidence`, `unresolved`,
`provider_failed`, `mapping_failed` y `not_reported` no son evidencia
negativa. Un valor `0.0` con origen `missing`, `derived` o `proxy` permanece no
explícito.

`not_detected_with_method` es diferente: puede ser evaluable únicamente cuando
se documenta el alcance del método, la fuente y el mapeo directo.

## Independencia

El resumen conserva dos conteos:

- número de variables explícitas distintas;
- número de grupos de evidencia independientes.

Esto evita presentar tres transformaciones del mismo conjunto de datos como
tres evidencias biológicas independientes. Stage 4A sólo reporta ambos
conteos; no modifica todavía el umbral del núcleo de scoring.

## Mapeo

Son directos:

- `exact_accession`;
- `exact_sequence_md5`;
- `exact_locus_tag`;
- `exact_gene_and_taxon`.

`family_match` y `ortholog_match` son evidencia de apoyo. Por defecto no
habilitan un score respaldado, salvo una política futura explícita y auditada.

## Alcance científico

Superar el contrato significa que existe evidencia trazable suficiente para
calcular una salida respaldada. No constituye validación experimental de un
blanco ni demuestra capacidad predictiva sobre evolución de resistencia.
