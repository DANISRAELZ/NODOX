# User-Curated Template Audit

## Proposito

Esta auditoria revisa las plantillas de `data_templates/` contra el protocolo
`user_curated`. El objetivo es verificar si un usuario puede preparar datos
reales, trazables y separados de `controlled_reference`, demo, proxy, cache y
online sin modificar scoring ni ejecutar el pipeline.

La conclusion general es conservadora: las plantillas obligatorias cubren los
campos tecnicos minimos para que el pipeline pueda leer capas reales, mientras
que `data_templates/user_curated_dataset_manifest_template.csv` cubre la
trazabilidad minima a nivel de dataset. No todas las plantillas biologicas
incluyen por fila todos los metadatos `user_curated`; por ahora esos metadatos
deben declararse en el manifest o documentacion equivalente.

## Criterios usados

Campos minimos de manifest para un dataset real `user_curated`:

- `organism`
- `strain`
- `dataset_id`
- `dataset_version`
- `curator_name`
- `curation_date`
- `source_type`
- `evidence_status`
- `evidence_kind`
- `provenance`
- `input_file`
- `input_schema`
- `required_for_scoring`
- `notes`

Campos minimos por fila para capas biologicas:

- identificador: `protein_id` o identificador equivalente;
- nombre legible cuando exista: `gene`;
- variable biologica propia de la capa;
- procedencia minima: `database`, `source_database`, `evidence_source`,
  `evidence_source_type`, referencia o notas;
- valores faltantes, proxy o inferidos declarados de forma explicita cuando
  corresponda.

## Plantillas revisadas

| Plantilla | Prioridad para `user_curated` | Proposito | Campos minimos esperados | Estado y brechas |
| --- | --- | --- | --- | --- |
| `essentiality_template.csv` | Obligatoria | Esencialidad o fitness del candidato. | `protein_id`, `gene`, `essential`, `evidence`, `database`. | Cubre scoring minimo y una procedencia basica. Brecha: no incluye curador, version ni estado de evidencia por fila; usar manifest. |
| `virulence_template.csv` | Obligatoria | Virulencia o contribucion a patogenicidad. | `protein_id`, `gene`, `virulence_score`, `virulence_factor`, `database`. | Cubre scoring minimo. Brecha: falta campo explicito de tipo/referencia de evidencia; usar manifest o notas externas. |
| `human_homologs_template.csv` | Obligatoria | Riesgo por homologia o similitud con hospedero humano. | `protein_id`, `gene`, campos de hit humano, metrica de similitud, metodo, fuente, confianza y `database`. | Es la plantilla obligatoria mas completa para trazabilidad. Brecha menor: metadatos de dataset quedan en manifest. |
| `localization_template.csv` | Obligatoria | Localizacion subcelular y accesibilidad aproximada. | `protein_id`, `gene`, `localization`, `database`. | Cubre scoring minimo. Brecha: no distingue evidencia experimental, prediccion, literatura o base externa; usar manifest. |
| `functional_network_template.csv` | Recomendada | Centralidad, cuello de botella, redundancia y dependencia funcional. | `protein_id`, `gene`, metricas de red, `database`. | Cubre variables de red. Brecha: no describe como se construyo la red, version, umbral ni fuente primaria; usar manifest. |
| `strain_conservation_template.csv` | Recomendada | Conservacion entre cepas, aislados o linajes. | `protein_id`, `gene`, conservacion, cobertura, carga de variantes, `database`. | Cubre variables principales. Brecha: no declara panel de cepas ni criterio de inclusion; usar manifest. |
| `host_annotation_template.csv` | Recomendada | Solapamiento de dominios y criticidad potencial del hospedero. | `protein_id`, `gene`, `domain_overlap_score`, `host_criticality_penalty`, `database`. | Cubre entrada compacta. Brecha: no incluye metodo, version ni referencia; usar manifest y, si aplica, reporte del proveedor. |
| `literature_support_template.csv` | Recomendada | Soporte bibliografico curado por candidato. | `protein_id`, `gene`, organismo/contexto, tipo de evidencia, cita, DOI/PubMed, fuerza, notas y `database`. | Cubre bien procedencia bibliografica. Brecha: no reemplaza manifest de dataset. |
| `clinical_impact_template.csv` | Recomendada | Danio al hospedero, severidad e impacto clinico contextual. | `protein_id`, `gene`, scores clinicos, tipo/referencia/notas de evidencia, `database`. | Cubre contexto clinico curado. Brecha: los scores pueden ser proxies si no se declara evidencia; el manifest debe indicar alcance. |
| `curated_disease_context_template.csv` | Recomendada | Contexto de enfermedad, etapa de infeccion y relevancia contextual. | `protein_id`, `gene`, `infection_context_score`, contexto, etapa, tipo/referencia/notas, `database`. | Cubre trazabilidad contextual razonable. Brecha: no declara curador/version por fila; usar manifest. |
| `therapy_site_context_template.csv` | Recomendada | Sitio de infeccion, acceso y contexto terapeutico. | `protein_id`, `gene`, acceso, sitio, tipo/referencia/notas, enfermedad/sindrome, `database`. | Cubre evidencia de accesibilidad. Brecha: requiere cuidado para separar accesibilidad medida de proxy. |
| `contextual_essentiality_template.csv` | Recomendada | Esencialidad contextual, pleiotropia y lectura de nodo funcional. | `protein_id`, `gene`, scores de contexto/teoria, calidad, techo de confianza, fuente, notas y flags. | Cubre trazabilidad Fase 3. Brecha: los scores conceptuales requieren justificacion externa en manifest/notas. |
| `evolutionary_escape_template.csv` | Recomendada | Evidencia evolutiva amplia sobre escape, tolerancia, compensacion y costo. | `protein_id`, `gene`, variables de escape, evidencia, fuente, notas, calidad y flags. | Muy completa. Brecha: puede mezclar evidencia observada e inferida; documentar `evidence_kind` y limites en manifest. |
| `evolutionary_escape_risk_template.csv` | Recomendada | Riesgo de escape evolutivo descompuesto. | `candidate_id`, `gene`, `protein_id`, `organism`, `strain`, variables de riesgo/proteccion, fuente, tipo, confianza, notas. | Cubre organismo/cepa y fuente por fila. Brecha: no usa exactamente `source_type=user_curated`; manifest debe separar categorias. |
| `redundancy_template.csv` | Recomendada | Paralogia, backups funcionales y rutas alternativas. | `protein_id`, `gene`, paralogia, alternativas, evidencia, calidad, fuente, notas y `database`. | Cubre trazabilidad de redundancia. Brecha: panel/metodo de busqueda debe ir en manifest. |
| `collateral_sensitivity_template.csv` | Recomendada | Sensibilidad colateral y oportunidades de combinacion. | `protein_id`, `gene`, scores, clase/pareja de combinacion, referencia, racional, calidad, fuente y notas. | Cubre evidencia de combinacion. Brecha: no debe interpretarse como recomendacion terapeutica sin validacion externa. |
| `evidence_quality_template.csv` | Recomendada | Calidad de evidencia, techo de confianza y flags de auditoria. | `protein_id`, `gene`, calidad, techo, tipo de fuente, notas, flags y `database`. | Cubre auditoria por candidato. Brecha: complementa, pero no sustituye, el manifest por dataset. |
| `organism_profile_template.csv` | Recomendada | Perfil de organismo, cepa, taxonomia, fuentes y disponibilidad de capas. | `organism`, `strain`, taxonomia, accesiones/fuentes, disponibilidad, curador, fecha y notas. | Cubre alcance del organismo. Brecha: no enumera cada archivo de entrada; usar manifest. |
| `user_curated_dataset_manifest_template.csv` | Recomendada para toda validacion real | Manifest de trazabilidad por dataset curado. | Todos los campos minimos `user_curated` definidos arriba. | Cubre la brecha principal de trazabilidad a nivel dataset. No alimenta scoring. |
| `biological_validation_targets.csv` | Opcional operativa | Priorizacion manual de candidatos para validacion biologica posterior. | Identificador, organismo/cepa, ranking/score, evidencias, rol, estado, prioridad, notas, curador y fecha. | Util para revision experimental. Brecha: es una tabla operativa, no entrada minima de scoring. |
| `organism_config_template.yaml` | Opcional operativa | Configuracion declarativa de organismo, hospedero, sitio, modo y fuentes externas. | organismo, cepa, taxon, contexto, `allow_demo_data`, fuentes externas y notas. | Util para preparar una corrida. Brecha: `analysis_mode` puede mencionar fuentes externas; para fase `user_curated` offline deben mantenerse desactivadas o documentadas. |

## Archivos de ejemplo incluidos

Tambien existen CSV sin sufijo `_template` en `data_templates/` para algunas
capas. Esos archivos sirven como ejemplos o esqueletos de compatibilidad. No
deben interpretarse como evidencia `user_curated` real hasta que el usuario
reemplace sus filas por datos propios y registre el archivo en el manifest.

## Brechas detectadas

- Las plantillas obligatorias `essentiality`, `virulence` y `localization`
  dependen de `database` como procedencia minima; no incluyen por fila
  `source_type`, `evidence_status`, `curator_name`, version ni fecha.
- Varias plantillas recomendadas incluyen referencias o notas, pero no un
  vocabulario uniforme para distinguir `user_curated`, `controlled_reference`,
  demo, proxy, cache y online.
- La trazabilidad completa de organismo, cepa, curador, version, archivo de
  entrada y obligatoriedad para scoring queda centralizada en
  `user_curated_dataset_manifest_template.csv`, no duplicada en cada capa.
- Las plantillas que aceptan scores derivados requieren notas claras para no
  presentar proxies o inferencias como evidencia observada.
- `organism_config_template.yaml` es util para contexto, pero no reemplaza el
  manifest porque no documenta cada dataset individual.

## Recomendaciones futuras

- Mantener por ahora los esquemas de capas estables y usar el manifest para
  trazabilidad de dataset, evitando cambios prematuros en validacion o scoring.
- En una fase posterior, evaluar si conviene agregar columnas opcionales
  uniformes como `source_type`, `evidence_status`, `evidence_kind` y
  `provenance` a las capas obligatorias.
- Definir un vocabulario controlado para `source_type` que preserve la
  separacion entre `user_curated`, `controlled_reference`, demo, proxy, cache y
  online.
- Agregar ejemplos documentales de manifest, sin datos de organismos especificos,
  antes de automatizar validaciones nuevas.
- No conectar estas recomendaciones a importacion ni scoring hasta tener un
  dataset real revisado por el usuario.
