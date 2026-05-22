# User-Curated Minimal Real Dataset

## Proposito

Esta guia describe el dataset minimo controlado para probar el flujo con datos
ingresados manualmente por el usuario antes de interpretar scoring real. El
objetivo es verificar que Nodos Funcionales mantenga separadas la evidencia
`user_curated`, la evidencia incompleta, las proxies marcadas y la evidencia
faltante.

Este minimo no valida eficacia terapeutica. Tampoco convierte una tabla pequena
en predictor clinico. Para la preparacion general de staging, manifest y
procedencia antes de importar, ver
`docs/user_curated_real_dataset_readiness.md`.

## Paquete minimo

Crear un paquete local en `user_curated_staging/<project_id>/` con:

```text
manifest.csv
raw_inputs/essentiality.csv
raw_inputs/virulence.csv
raw_inputs/human_homologs.csv
raw_inputs/localization.csv
notes/
provenance/
```

Las cuatro capas minimas deben referirse al mismo organismo bacteriano y al
alcance declarado para la corrida. Cada archivo debe tener al menos una fila
real con un `protein_id` trazable del usuario. No copiar filas demo, snapshots
`controlled_reference`, cache ni respuestas online frescas como evidencia
principal.

## Archivos y columnas obligatorias

Usar los encabezados de `data_templates/`. Para el minimo controlado:

| Archivo | Plantilla | Columnas obligatorias |
| --- | --- | --- |
| `essentiality.csv` | `data_templates/essentiality_template.csv` | `protein_id`, `gene`, `essential`, `evidence`, `database` |
| `virulence.csv` | `data_templates/virulence_template.csv` | `protein_id`, `gene`, `virulence_score`, `virulence_factor`, `database` |
| `human_homologs.csv` | `data_templates/human_homologs_template.csv` | Todas las columnas de la plantilla; al menos `protein_id`, `gene`, campos de hit/ortologia, `evidence_source_type`, notas de curacion y `database` deben conservarse para auditar seguridad del hospedero. |
| `localization.csv` | `data_templates/localization_template.csv` | `protein_id`, `gene`, `localization`, `database` |

El manifest usa exactamente las columnas de
`data_templates/user_curated_dataset_manifest_template.csv`:

```text
organism,strain,dataset_id,dataset_version,curator_name,curation_date,source_type,evidence_status,evidence_kind,provenance,input_file,input_schema,required_for_scoring,notes
```

Agregar una fila de manifest por cada archivo minimo. En este flujo las cuatro
filas deben declarar `required_for_scoring=true` solo si el usuario ya acepto
que esas capas son las entradas controladas que se usaran para la prueba.
Cada archivo debe seguir el template declarado en `manifest.input_schema`.

## Esquema de importacion y trazabilidad

El importador crea dos rastros distintos:

- la capa interna normalizada en `workspace/data_raw/<dataset>.csv`;
- una copia del CSV original en `workspace/data_raw/source_exports/`.

La capa interna conserva las columnas contempladas por el dataset y por su
template. Columnas libres o no mapeadas pueden quedar solo en
`data_raw/source_exports/` o no aparecer en el CSV interno. Por eso, para
conservar trazabilidad dentro de `essentiality.csv`, usar las columnas del
template como `evidence` y `database`.

No usar columnas libres como `essentiality_score` o `essentiality_call`
esperando que aparezcan en la capa interna `essentiality.csv`, salvo que el
esquema se amplie formalmente. Si una nota adicional todavia es necesaria,
mantenerla en el export original, en el manifest, en `notes/` o en una columna
ya aceptada por el template correspondiente.

## Variables y reglas de esta prueba

Este minimo observa cuatro ejes ya soportados por el pipeline:

- esencialidad desde `essential` y `evidence`;
- virulencia desde `virulence_score` y `virulence_factor`;
- seguridad frente al hospedero desde los campos de hit y ortologia de
  `human_homologs.csv`;
- localizacion desde `localization`.

Las reglas de la prueba son simples: cada eje debe venir de una capa declarada
por el usuario, todo faltante relevante se documenta, toda proxy queda marcada
y ninguna ausencia se convierte en bajo riesgo.

## Registrar procedencia real

La categoria de fuente real se registra en el manifest como:

```text
source_type=user_curated
```

El campo `provenance` no debe quedarse solo como `user_curated`. Debe explicar
la fuente revisable: experimento, export local, literatura curada, catalogo
revisado, herramienta y version cuando aplique, o nota de curacion manual.
Si una nota operativa pide registrar `provenance=user_curated`, en este esquema
esa intencion se expresa con `source_type=user_curated` y un `provenance`
descriptivo.

Ejemplos de lectura correcta:

| Campo | Valor esperado |
| --- | --- |
| `source_type` | `user_curated` |
| `evidence_status` | `reviewed`, `pending_review` o estado equivalente declarado |
| `evidence_kind` | `experimental`, `literature`, `local_export` o combinacion documentada |
| `provenance` | Descripcion trazable de fuente, version, referencia o export revisado |
| `notes` | Faltantes, conflictos, proxies aceptadas y alcance de la fila |

Si una evidencia solo es inferida o aproximada, no presentarla como medicion
directa. Separarla en notas o columnas de fuente y describirla como proxy o
incompleta.

## Evidencia incompleta, proxy y faltante

Para este minimo controlado, una celda vacia significa que falta informacion o
que el archivo no la aporta. No significa automaticamente bajo riesgo, ausencia
biologica ni evidencia negativa.

Marcar la incompletitud antes de correr scoring:

- usar `evidence_status` y `notes` del manifest para indicar `pending`,
  `incomplete`, faltantes aceptados o revision pendiente;
- conservar notas de curacion en columnas disponibles, por ejemplo
  `curator_notes` y `orthology_evidence_note` en `human_homologs.csv`;
- describir en `notes/` cualquier campo vacio relevante y por que no se
  completo;
- si un valor es proxy, declararlo como proxy en la procedencia o notas y no
  mezclarlo con la fila observada sin marca.

Ejemplos conservadores:

| Situacion | Como documentarla | Lectura permitida |
| --- | --- | --- |
| No hay evidencia curada de homologia para un candidato | Nota de faltante y estado incompleto | Riesgo del hospedero no resuelto |
| Localizacion estimada por heuristica | Fuente y nota `proxy` | Accesibilidad exploratoria |
| Virulencia revisada pero sin contexto de sitio de infeccion | Nota de evidencia incompleta | Prioridad puede existir con confianza limitada |

## Validar antes de scoring

1. Validar el paquete y el manifest:

```powershell
.\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>
```

2. Si se revisa solo el manifest:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\<project_id>\manifest.csv
```

3. Importar cada capa solo despues de revision manual, con manifest
   prevalidado:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace <workspace_dedicado> --dataset essentiality --input user_curated_staging\<project_id>\raw_inputs\essentiality.csv --validate-user-curated-manifest user_curated_staging\<project_id>\manifest.csv
```

Repetir la importacion para `virulence`, `human_homologs` y `localization` en el
mismo workspace dedicado. No usar `--allow-demo-data` para interpretar esta
prueba como `user_curated`.

Antes de scoring revisar:

- que las cuatro capas minimas tienen filas del organismo declarado;
- que cada archivo importado sigue el template indicado en
  `manifest.input_schema`;
- que los `protein_id` que se quieren comparar se alinean entre capas o que la
  falta de alineacion queda documentada;
- que `source_type=user_curated` no se usa para demo, proxy, cache, online
  fresco ni `controlled_reference`;
- que vacios, proxies y faltantes estan visibles en manifest, notas o columnas
  auditables.

## Lectura conservadora de resultados

Despues de correr una prueba controlada, interpretar prioridad y confianza por
separado:

- `therapeutic_priority_score` ordena hipotesis terapeuticas dentro del modelo;
- `evidence_confidence_score` describe el soporte disponible para leerlas;
- score alto con confianza baja sigue siendo exploratorio;
- score bajo con evidencia incompleta no descarta el nodo;
- bajo riesgo aparente con faltantes o proxies sigue siendo riesgo no resuelto.

La lectura conservadora debe advertir sobre evidencia proxy, baja confianza,
redundancia alta, `paralog_count` alto, `mobile_context`, `hgt_context`,
`recombination_context` y `resistance_association` cuando existan. La subcapa
evolutiva modula riesgo de escape sin opacar funcionalidad, selectividad,
accesibilidad ni procedencia.

## Documentos relacionados

- `docs/user_curated_validation_protocol.md`: reglas completas para la
  validacion real `user_curated`.
- `docs/user_curated_validation_checklist.md`: checklist para aceptar o detener
  la importacion.
- `docs/user_curated_conservative_interpretation.md`: tabla interpretativa de
  prioridad, confianza y riesgo.
- `docs/dataset_import.md`: uso del importador y prevalidacion del manifest.

## Paso futuro sugerido

Despues de que este minimo controlado pase validacion estructural, revisar el
workspace dedicado y decidir si la primera corrida de scoring `user_curated`
tiene evidencia suficiente para ser exploratoria o si debe detenerse por
faltantes, proxies o procedencia aun incompleta.
