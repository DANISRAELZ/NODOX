# User-Curated Validation Checklist

## Proposito

Este checklist se usa antes de importar datos o ejecutar el pipeline. Su funcion
es decidir si un conjunto de archivos puede tratarse como dataset real
`user_curated`, manteniendo separadas las categorias `controlled_reference`,
demo, proxy, cache y online.

Completar este checklist no valida eficacia terapeutica. Solo confirma que los
datos tienen identidad, procedencia y formato suficientes para pasar a una fase
de importacion o preparacion de workspace.

## 1. Identificacion del organismo

- [ ] El organismo esta declarado como `<organism_name>`.
- [ ] La cepa, aislado, linaje o conjunto de cepas esta declarado como
  `<strain_or_isolate>`.
- [ ] El alcance taxonomico esta escrito en notas del dataset o perfil del
  organismo.
- [ ] Los identificadores de proteina o gen corresponden al organismo y alcance
  declarados.
- [ ] No hay identificadores residuales de organismos demo o ejemplos de
  plantilla.

Detener la validacion si no puede confirmarse el organismo, cepa/aislado o
alcance taxonomico de los archivos.

## 2. Separacion de fuentes

- [ ] Los archivos no provienen de `data_demo/`.
- [ ] Los archivos no son snapshots o referencias `controlled_reference`.
- [ ] Los archivos no son solo cache reutilizado sin revision del usuario.
- [ ] Los archivos no dependen de una consulta online fresca para interpretarse.
- [ ] Los valores proxy, inferidos o faltantes estan marcados en columnas,
  notas o manifest.
- [ ] Si una capa mezcla fuentes, cada fila o archivo separa claramente
  `user_curated`, `controlled_reference`, demo, proxy, cache y online.

Detener la validacion si la evidencia principal de las capas obligatorias es
demo, proxy, cache no revisado, online fresco no auditado o referencia
controlada.

## 3. Manifest `user_curated`

Usar `data_templates/user_curated_dataset_manifest_template.csv` como guia.
Como prevalidacion estructural opcional antes de importar, puede llamarse
`validate_user_curated_manifest()` desde Python. Esta funcion devuelve errores
del manifest, pero no valida biologicamente el dataset ni calcula scores.

- [ ] Existe un manifest para los archivos a revisar o una documentacion
  equivalente.
- [ ] Cada archivo de entrada tiene una fila en el manifest.
- [ ] `organism` esta completo.
- [ ] `strain` esta completo o indica explicitamente el alcance si no aplica.
- [ ] `dataset_id` identifica la capa o coleccion de forma estable.
- [ ] `dataset_version` permite distinguir revisiones.
- [ ] `curator_name` identifica al responsable de la curacion.
- [ ] `curation_date` esta en formato fecha claro.
- [ ] `source_type` usa `user_curated` para evidencia real de usuario.
- [ ] `evidence_status` indica si la evidencia esta revisada, pendiente o
  incompleta.
- [ ] `evidence_kind` distingue experimento, literatura, export local,
  anotacion revisada, inferencia o combinacion.
- [ ] `provenance` describe fuente, herramienta, cita, catalogo o export.
- [ ] `input_file` coincide con un archivo presente.
- [ ] `input_schema` apunta a la plantilla o esquema usado.
- [ ] `required_for_scoring` indica si la capa es obligatoria para iniciar
  scoring.
- [ ] `notes` documenta limites, faltantes, proxies o conflictos.

Detener la validacion si falta manifest para capas obligatorias o si
`source_type` no separa datos reales de usuario de demo/proxy/cache/online.

## 4. Archivos de entrada presentes

Capas obligatorias para una validacion inicial:

- [ ] `essentiality.csv`
- [ ] `virulence.csv`
- [ ] `human_homologs.csv`
- [ ] `localization.csv`

Capas recomendadas cuando existan datos reales:

- [ ] `functional_network.csv`
- [ ] `strain_conservation.csv`
- [ ] `host_annotation.csv`
- [ ] `literature_support.csv`
- [ ] `clinical_impact.csv`
- [ ] `curated_disease_context.csv`
- [ ] `therapy_site_context.csv`
- [ ] `contextual_essentiality.csv`
- [ ] `evolutionary_escape.csv`
- [ ] `evolutionary_escape_risk.csv`
- [ ] `redundancy.csv`
- [ ] `collateral_sensitivity.csv`
- [ ] `evidence_quality.csv`
- [ ] `organism_profile.csv` o documentacion equivalente.

Detener la validacion si falta una capa obligatoria y no existe una decision
documentada de trabajar solo en preparacion, sin importacion ni pipeline.

## 5. Esquemas esperados

- [ ] Cada archivo usa encabezados compatibles con su plantilla en
  `data_templates/`.
- [ ] Cada capa biologica tiene `protein_id` o identificador equivalente.
- [ ] Cada capa biologica tiene `gene` cuando el dato este disponible.
- [ ] Cada capa contiene la variable biologica propia de su proposito.
- [ ] Cada capa declara procedencia minima con `database`, `source_database`,
  `evidence_source`, `evidence_source_type`, referencia, notas o manifest.
- [ ] No hay filas de ejemplo como `<organism_name>`, `<dataset_id>` o
  `EXAMPLE_PROTEIN` en archivos que se quieren importar como evidencia real.

Detener la validacion si los encabezados no pueden mapearse a las plantillas o
si los identificadores principales estan vacios.

## 6. Evidencia minima aceptable

Para aceptar un archivo como `user_curated`:

- [ ] Tiene al menos una fila real del organismo declarado.
- [ ] La procedencia es trazable.
- [ ] El usuario reviso o aporto la evidencia.
- [ ] Los valores observados se distinguen de inferencias o proxies.
- [ ] Las referencias, versiones de herramienta, catalogos o notas existen
  cuando son necesarias para interpretar la capa.

Para aceptar el conjunto completo para importacion:

- [ ] Las cuatro capas obligatorias estan presentes y trazables.
- [ ] La mayoria de la evidencia principal proviene de `user_curated`.
- [ ] Los faltantes no impiden distinguir esencialidad, virulencia, homologia
  humana y localizacion.
- [ ] El manifest cubre todos los archivos obligatorios.

## 7. Campos faltantes

Permitidos si estan documentados:

- [ ] `gene` faltante cuando `protein_id` sea estable y trazable.
- [ ] Campos recomendados de capas opcionales ausentes.
- [ ] Scores contextuales o evolutivos faltantes si la capa no se usara aun.
- [ ] Referencias bibliograficas faltantes cuando la evidencia provenga de un
  experimento o export local documentado de otra forma.

No permitidos para aceptar importacion:

- [ ] `protein_id` vacio en capas biologicas.
- [ ] `organism` o `strain`/alcance ausente en manifest o documentacion.
- [ ] `source_type` ausente o ambiguo para capas obligatorias.
- [ ] Procedencia completamente ausente.
- [ ] Filas de plantilla o demo mezcladas con evidencia real.
- [ ] Valores proxy presentados como evidencia observada.

## 8. Limites interpretativos

- [ ] El dataset no demuestra eficacia terapeutica.
- [ ] Nodos Funcionales se presenta como plataforma de priorizacion terapeutica
  basada en evidencia, no como predictor clinico definitivo.
- [ ] Un score futuro alto no confirmara seguridad, accesibilidad real ni
  validez clinica.
- [ ] `therapeutic_priority_score` futuro y `evidence_confidence_score` futuro
  se leeran por separado.
- [ ] Un score alto futuro no equivaldra automaticamente a confianza alta.
- [ ] Datos insuficientes no equivalen a evidencia negativa.
- [ ] Ausencia de evidencia, datos incompletos o proxy no equivalen a bajo
  riesgo.
- [ ] Proxy o inferencia no deben presentarse como medicion directa.
- [ ] Riesgo evolutivo modula la interpretacion sin opacar funcionalidad,
  selectividad, accesibilidad ni evidencia.
- [ ] Cache y online pueden ayudar a reproducibilidad o enriquecimiento futuro,
  pero no sustituyen evidencia `user_curated` en esta fase.
- [ ] `controlled_reference` sirve para contratos y comparacion metodologica,
  no como evidencia del organismo nuevo.

## 9. Criterios para detener la validacion

Detener antes de importar si ocurre cualquiera de estos casos:

- falta organismo, cepa/aislado o alcance;
- faltan archivos obligatorios sin justificacion documentada;
- no existe manifest ni documentacion equivalente;
- la procedencia principal es demo, proxy, cache no revisado, online fresco o
  `controlled_reference`;
- los identificadores principales estan vacios o no pertenecen al organismo;
- hay filas de ejemplo no reemplazadas;
- no puede distinguirse evidencia observada de inferencia;
- el usuario no puede explicar la fuente de los datos.

## 10. Criterios para aceptar importacion

Aceptar el dataset para importacion si se cumplen todos estos puntos:

- organismo y cepa/aislado estan identificados;
- los archivos obligatorios existen y usan esquemas compatibles;
- el manifest esta completo para cada archivo obligatorio;
- `source_type=user_curated` esta reservado para evidencia real de usuario;
- demo, proxy, cache, online y `controlled_reference` estan ausentes o
  claramente marcados como no principales;
- cada archivo tiene procedencia suficiente;
- los faltantes permitidos estan documentados;
- los limites interpretativos estan aceptados antes de ejecutar cualquier
  importacion o pipeline.

Una vez aceptado, el siguiente paso es importar o preparar el workspace usando
los comandos documentados, sin modificar scoring y sin mezclar outputs de fases
anteriores.
