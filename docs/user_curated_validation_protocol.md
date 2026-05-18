# User-Curated Validation Protocol

## Objetivo

Este protocolo define como preparar una validacion con datos reales curados por
el usuario para un organismo bacteriano nuevo. La meta es demostrar que Nodos
Funcionales puede recibir evidencia especifica del organismo, ejecutar el
pipeline sin datos demo, snapshots controlados, cache mutable ni evidencia
online fresca, y producir un ranking terapeutico interpretable dentro de la
Teoria de Nodos Funcionales.

La validacion `user_curated` no busca demostrar eficacia clinica. Solo valida
que el software operacionaliza la teoria con datos trazables del usuario y que
separa procedencia, confianza, faltantes y limites de interpretacion.

En la fase de entrada con archivos reales, `user_curated` tambien define el
paquete local de trabajo que se prepara antes de importar datos. Ese paquete
puede incluir anotaciones funcionales, listas de genes, conservacion,
virulencia, esencialidad, exports externos revisados y curacion manual. La
preparacion de esos archivos no ejecuta pipeline, no calcula scoring y no
convierte automaticamente evidencia debil en evidencia fuerte.

## Definicion de `user_curated`

Dentro de este proyecto, `user_curated` significa evidencia preparada,
aportada o revisada por el usuario para el organismo y la cepa que se estan
validando. Debe ser evidencia biologica real del caso de estudio, no una tabla
incluida para demostrar el software ni una respuesta automatica usada sin
revision.

Un dataset puede describirse como `user_curated` cuando cumple estas
condiciones:

- corresponde al organismo, cepa, aislado, linaje o conjunto de cepas declarado
  para la corrida;
- conserva identificadores trazables, preferentemente `protein_id` y `gene`;
- declara su procedencia en columnas como `database`, `source_database`,
  `evidence_source_type`, `evidence_source`, `curator_notes`,
  `evidence_notes` o `notes`;
- puede explicarse con una fuente, experimento, export local, catalogo revisado
  o cita bibliografica;
- separa valores observados de valores inferidos, proxy o faltantes;
- fue revisado por una persona antes de usarse para interpretar el ranking.

`user_curated` no exige que toda la evidencia sea experimental. Puede incluir
literatura curada, exports de herramientas locales, anotaciones revisadas,
catalogos internos o evidencia externa ya evaluada por el usuario. Lo importante
es que la fuente sea especifica, trazable y declarada.

## Alcance

La corrida debe hacerse en un workspace separado para el organismo evaluado. No
debe reutilizar `results/`, `data_processed/`, `data_sessions/` existentes,
snapshots curados ni cache taxonomico como evidencia biologica. PAO1,
Corynebacterium y H37Rv siguen siendo ejemplos o referencias controladas, no el
centro de esta validacion.

No deben ejecutarse llamadas online. Si despues se desea comparar STRING,
UniProt u otro proveedor, eso debe ocurrir en una fase `online_optional`
separada, con protocolo y workspace propios.

## Estructura esperada de staging

Los archivos reales deben organizarse primero en una carpeta local ignorada por
Git:

```text
user_curated_staging/<dataset_id>/
  README.md
  manifest.csv
  raw_inputs/
  notes/
  provenance/
```

Uso esperado:

- `README.md`: resumen local del paquete, alcance, curador, estado de revision
  y limites. No debe contener datos sensibles completos.
- `manifest.csv`: copia local del manifest basado en
  `data_templates/user_curated_dataset_manifest_template.csv`.
- `raw_inputs/`: ubicacion local para archivos reales, como anotaciones
  funcionales, lista de genes, tablas de conservacion, virulencia,
  esencialidad, exports externos o tablas curadas manualmente.
- `notes/`: decisiones de curacion, exclusiones, dudas, faltantes y conflictos.
- `provenance/`: referencias, versiones de herramientas, citas, descripciones
  de export y trazabilidad de origen.

La carpeta `user_curated_staging/` es local e ignorada por `.gitignore`. No debe
agregarse al repositorio ni mezclarse con `results/`, `data_processed/`,
`data_sessions/`, snapshots curados o datos demo.

## Archivos minimos obligatorios

Para que el pipeline tenga candidatos reales sin habilitar demo, el usuario debe
preparar al menos estas capas en el workspace:

```text
data_raw/essentiality.csv
data_raw/virulence.csv
data_raw/human_homologs.csv
data_raw/localization.csv
```

Tambien puede importarlas con `import_dataset.py`, que materializa los CSVs en
`workspace/data_raw/` y conserva copias del export original en
`workspace/data_raw/source_exports/`.

Ademas, se recomienda mantener un manifest de datasets curados usando
`data_templates/user_curated_dataset_manifest_template.csv`. Ese manifest no
alimenta el scoring; sirve para declarar, por cada archivo de usuario, organismo,
cepa, version, curador, procedencia, estado de evidencia, esquema usado y si la
capa es requerida para scoring.

El manifest puede prevalidarse con
`validate_user_curated_manifest()` antes de importar datos. Esta revision es
estructural y de procedencia minima; no equivale a validacion biologica, scoring
ni aceptacion cientifica del dataset.

Columnas minimas esperadas segun `data_templates/`:

| Archivo | Columnas principales |
| --- | --- |
| `essentiality.csv` | `protein_id`, `gene`, `essential`, `evidence`, `database` |
| `virulence.csv` | `protein_id`, `gene`, `virulence_score`, `virulence_factor`, `database` |
| `human_homologs.csv` | `protein_id`, `gene`, `human_hit_id`, `human_hit_name`, `percent_identity`, `query_coverage`, `subject_coverage`, `evalue`, `bit_score`, `shared_domain_count`, `orthology_method`, `source_database`, `evidence_source_type`, `curator_notes`, `human_homolog`, `human_gene`, `human_uniprot_accession`, `orthology_tool`, `orthology_version`, `orthology_reference`, `orthology_confidence_score`, `orthology_evidence_note`, `database` |
| `localization.csv` | `protein_id`, `gene`, `localization`, `database` |

Cada archivo debe contener al menos una fila real para un candidato del
organismo. Los identificadores deben referirse al organismo y cepa evaluados, no
a un organismo demo.

## Entradas esperadas desde `data_templates/`

Los archivos deben seguir los encabezados de `data_templates/`. Esta lista
resume los insumos esperados o recomendados para una validacion `user_curated`.

| Prioridad | Archivo en el workspace | Plantilla de referencia | Uso |
| --- | --- | --- | --- |
| Obligatorio | `data_raw/essentiality.csv` | `data_templates/essentiality_template.csv` | Evidencia de esencialidad o fitness del candidato. |
| Obligatorio | `data_raw/virulence.csv` | `data_templates/virulence_template.csv` | Evidencia de virulencia o contribucion a patogenicidad. |
| Obligatorio | `data_raw/human_homologs.csv` | `data_templates/human_homologs_template.csv` | Riesgo por similitud u homologia con hospedero humano. |
| Obligatorio | `data_raw/localization.csv` | `data_templates/localization_template.csv` | Localizacion subcelular y acceso aproximado. |
| Recomendado | `data_raw/functional_network.csv` | `data_templates/functional_network_template.csv` | Centralidad, cuello de botella, redundancia y dependencia funcional. |
| Recomendado | `data_raw/strain_conservation.csv` | `data_templates/strain_conservation_template.csv` | Conservacion entre cepas, linajes o aislados relevantes. |
| Recomendado | `data_raw/host_annotation.csv` | `data_templates/host_annotation_template.csv` | Solapamiento de dominios y criticidad potencial del hospedero. |
| Recomendado | `data_raw/literature_support.csv` | `data_templates/literature_support_template.csv` | Evidencia bibliografica trazable y notas de curacion. |
| Recomendado | `data_raw/clinical_impact.csv` | `data_templates/clinical_impact_template.csv` | Impacto clinico, dano al hospedero y severidad curada. |
| Recomendado | `data_raw/curated_disease_context.csv` | `data_templates/curated_disease_context_template.csv` | Contexto de enfermedad, etapa y relevancia durante infeccion. |
| Recomendado | `data_raw/therapy_site_context.csv` | `data_templates/therapy_site_context_template.csv` | Sitio de infeccion, accesibilidad y contexto terapeutico. |
| Recomendado | `data_raw/contextual_essentiality.csv` | `data_templates/contextual_essentiality_template.csv` | Esencialidad contextual, pleiotropia y lectura de nodo funcional. |
| Recomendado | `data_raw/evolutionary_escape.csv` | `data_templates/evolutionary_escape_template.csv` | Evidencia evolutiva curada, escape y compensacion. |
| Recomendado | `data_raw/evolutionary_escape_risk.csv` | `data_templates/evolutionary_escape_risk_template.csv` | Riesgo de escape evolutivo descompuesto por variables. |
| Recomendado | `data_raw/redundancy.csv` | `data_templates/redundancy_template.csv` | Paralogia, backups funcionales y rutas alternativas. |
| Recomendado | `data_raw/collateral_sensitivity.csv` | `data_templates/collateral_sensitivity_template.csv` | Sensibilidad colateral y oportunidades de combinacion. |
| Recomendado | `data_raw/evidence_quality.csv` | `data_templates/evidence_quality_template.csv` | Calidad de evidencia, techo de confianza y flags de auditoria. |
| Recomendado | `organism_profile.csv` o documentacion equivalente | `data_templates/organism_profile_template.csv` | Organismo, cepa, taxonomia, proteoma, curador y alcance. |
| Recomendado | `user_curated_dataset_manifest.csv` | `data_templates/user_curated_dataset_manifest_template.csv` | Manifest de trazabilidad por dataset curado; no modifica scores. |

Las plantillas con filas de ejemplo no convierten esos ejemplos en evidencia
real. Para esta fase, el usuario debe reemplazar los ejemplos por datos propios
o dejar la capa ausente y declarar el faltante.

Plantillas de entrada amplia para paquetes reales:

| Archivo real esperado | Plantilla de referencia | Uso |
| --- | --- | --- |
| `functional_annotations.csv` | `data_templates/functional_annotations_template.csv` | Anotaciones funcionales revisadas por proteina o gen. |
| `gene_list.csv` | `data_templates/gene_list_template.csv` | Inventario basico de genes/proteinas del paquete. |
| `conservation.csv` | `data_templates/conservation_template.csv` | Conservacion por alcance, cepas, aislados o linajes definidos. |
| `virulence.csv` | `data_templates/virulence_template.csv` | Evidencia de virulencia compatible con el pipeline. |
| `essentiality.csv` | `data_templates/essentiality_template.csv` | Evidencia de esencialidad compatible con el pipeline. |
| `external_sources.csv` | `data_templates/external_sources_template.csv` | Exports revisados de UniProt, STRING, VFDB, CARD u otras fuentes. |
| `manual_curation.csv` | `data_templates/manual_curation_template.csv` | Decisiones de curacion manual y notas trazables por candidato. |
| `manifest.csv` | `data_templates/user_curated_dataset_manifest_template.csv` | Declaracion de procedencia, version, esquema y estado por archivo. |

Columnas minimas recomendadas:

| Tipo de archivo | Columnas minimas |
| --- | --- |
| Anotaciones funcionales | `organism`, `strain`, `protein_id`, `gene`, `functional_annotation`, `source_database`, `evidence_status` |
| Lista de genes | `organism`, `strain`, `protein_id`, `gene`, `source_database`, `evidence_status` |
| Conservacion | `organism`, `strain`, `protein_id`, `gene`, `conservation_scope`, `source_database`, `evidence_status` |
| Fuentes externas | `organism`, `strain`, `protein_id`, `gene`, `source_database`, `source_record_id`, `evidence_status` |
| Curacion manual | `organism`, `strain`, `protein_id`, `gene`, `curator_name`, `curation_decision`, `evidence_status` |

## Capas recomendadas

Estas capas no son obligatorias para iniciar, pero aumentan interpretabilidad,
confianza y robustez evolutiva:

| Archivo | Uso principal |
| --- | --- |
| `functional_network.csv` | red funcional, centralidad, redundancia y dependencia |
| `strain_conservation.csv` | conservacion por cepas o linajes definidos |
| `literature_support.csv` | soporte bibliografico curado con DOI, PubMed o cita trazable |
| `evolutionary_escape_risk.csv` | riesgo de escape, restriccion evolutiva y evidencia de resistencia |
| `evidence_quality.csv` | techo de confianza y notas de auditoria Fase 3 |
| `contextual_essentiality.csv` | esencialidad contextual en nicho o infeccion |
| `clinical_impact.csv` | severidad, impacto clinico o contexto terapeutico curado |
| `therapy_site_context.csv` | sitio de infeccion, acceso y contexto de tratamiento |

La subcapa evolutiva debe conservar, cuando exista evidencia, las variables:
`evolutionary_escape_risk`, `evolutionary_constraint`,
`mutation_tolerance`, `pathway_redundancy`, `paralog_count`,
`mobile_context`, `hgt_context`, `recombination_context` y
`resistance_association`.

## Reglas de procedencia

La validacion debe separar estas categorias:

- `user_curated`: evidencia aportada o revisada por el usuario para el
  organismo y cepa evaluados; puede vivir en `data_raw/` despues de importarse o
  en `data_user/` si la corrida usa el resolvedor por capas.
- `controlled_reference`: referencia controlada, snapshot congelado o fixture
  estable usado para verificar contratos de estructura; no cuenta como evidencia
  real del usuario aunque sea biologicamente plausible.
- `demo`: datos pequenos para probar el software; no deben usarse en esta
  validacion.
- `proxy`: valor derivado o aproximado; puede mantener el pipeline operativo,
  pero baja confianza.
- `cache`: resultado reutilizado; puede servir para reproducibilidad tecnica,
  pero no debe mezclarse con evidencia curada nueva sin declararlo.
- `online`: respuesta fresca de proveedor externo; queda fuera de esta fase.

Para esta validacion, los CSVs deben declarar fuentes en columnas como
`database`, `source_database`, `evidence_source_type`, `evidence_source`,
`curator_notes`, `evidence_notes` o `notes`. Si una columna no existe en la
plantilla, la procedencia debe documentarse en el protocolo de la corrida y en
el workspace, no inferirse por silencio.

## Como distinguir fuentes

Antes de aceptar una capa como `user_curated`, revisar esta separacion:

| Categoria | Indicador practico | Uso permitido en esta fase |
| --- | --- | --- |
| `user_curated` | Archivo entregado/revisado por el usuario, especifico del organismo, con fuente declarada. | Si, como evidencia principal. |
| `controlled_reference` | Snapshot o referencia congelada para validar contratos, por ejemplo casos ya cerrados. | No como evidencia del organismo nuevo; solo comparacion metodologica. |
| `demo` | Archivo empaquetado, ejemplo pequeno, `allow-demo-data` o `example_curated_demo`. | No, salvo prueba tecnica separada. |
| `proxy` | Valor derivado, fallback o default explicito con bandera de proxy. | Solo como limitacion declarada; no sostiene una conclusion fuerte. |
| `cache` | Respuesta o capa reutilizada de una corrida anterior. | No como evidencia nueva del usuario; puede mencionarse para reproducibilidad tecnica. |
| `online` | Respuesta fresca de UniProt, STRING u otro proveedor. | No en este bloque; requiere fase `online_optional` separada. |

Si una capa mezcla categorias, debe separarlas antes de correr el pipeline o
dejar una nota clara por fila o por archivo. La interpretacion debe tomar la
categoria mas debil para cualquier candidato cuya evidencia principal dependa de
demo, proxy, cache o referencia controlada.

## Criterios minimos de aceptacion

Un dataset individual puede aceptarse como `user_curated` si cumple todos estos
puntos:

- usa el encabezado de su plantilla o un export importable con `import_dataset.py`;
- contiene `protein_id` no vacio y, cuando sea posible, `gene`;
- tiene al menos una fila real del organismo evaluado;
- no contiene filas de ejemplo como `EXAMPLE_PROTEIN` ni identificadores de
  organismos demo;
- declara procedencia suficientemente informativa en `database` u otra columna
  de fuente;
- esta registrado en un manifest `user_curated` o documentacion equivalente con
  `source_type=user_curated`;
- distingue evidencia directa, literatura, base externa revisada, inferencia,
  proxy y faltante;
- conserva referencias, version de herramienta, fecha, curador o notas cuando
  esos datos existen;
- no depende de una llamada online fresca para ser interpretable;
- no sobrescribe snapshots curados ni outputs versionados del repositorio.

La corrida completa puede aceptarse como validacion `user_curated` solo si las
cuatro capas obligatorias estan presentes, la mayoria de la evidencia principal
proviene de usuario, y los faltantes/proxies quedan visibles en reportes o notas
de auditoria.

## Comandos recomendados

Ejemplo de importacion por capa:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_NAME" --workspace data_sessions/user_curated_organism --dataset essentiality --input path\to\essentiality.csv
```

Ejemplo para importar un directorio con archivos nombrados por dataset:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_NAME" --workspace data_sessions/user_curated_organism --dataset virulence --input-dir path\to\user_data
```

La corrida de validacion debe ejecutarse sin `--allow-demo-data` y sin modos
online:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --organism "ORGANISM_NAME" --strain "STRAIN_NAME" --workspace data_sessions/user_curated_organism --mode compare --taxon-resolution-mode offline_only
```

Si se requiere evitar escritura de cache taxonomico durante pruebas del
protocolo, usar opciones existentes como `--no-write-taxon-cache` cuando el
comando las exponga.

## Criterios para aceptar ranking real

Puede declararse que hubo ranking real si se cumplen todos estos puntos:

- la corrida no uso `--allow-demo-data`;
- los candidatos provienen de CSVs del usuario para el organismo evaluado;
- `results/ranking_nodos.csv` existe en el workspace de validacion;
- los reportes no marcan los candidatos principales como demo/template;
- las capas obligatorias tienen filas reales y procedencia trazable;
- la confianza y los faltantes estan reportados junto con el ranking;
- cualquier proxy o dato incompleto queda marcado y no se presenta como
  evidencia fuerte;
- las variables evolutivas presentes se interpretan como subcapa de robustez y
  restriccion del escape, no como prueba absoluta de bajo riesgo.

## Score alto y confianza baja

Un score alto no equivale por si solo a evidencia fuerte. Si un candidato tiene
score alto pero baja confianza, faltantes relevantes, procedencia incompleta,
proxy marcado o evidencia derivada de cache/demo/referencia controlada, debe
interpretarse como hipotesis computacional priorizada, no como conclusion
terapeutica robusta.

La plataforma prioriza blancos terapeuticos bacterianos para exploracion y
revision. No sustituye validacion experimental, revision microbiologica,
evaluacion farmacologica, evaluacion clinica ni decisiones de uso terapeutico.

Para Fase 3, si se activa en otra corrida, `ranking_nodos_phase3_real_candidates.csv`
debe contener candidatos incluidos y el reporte debe indicar
`ranking_real_produced`. Si el estado es
`no_real_ranking_demo_template_or_insufficient_evidence`, la validacion no debe
presentarse como ranking terapeutico real de Fase 3.

## Criterios para datos insuficientes

Debe declararse `datos insuficientes` si ocurre cualquiera de estos casos:

- faltan las capas obligatorias;
- las capas existen pero no tienen filas para los mismos candidatos;
- la mayoria de senales proviene de proxy, demo, cache, snapshot o faltante;
- no hay procedencia trazable;
- no hay evidencia suficiente para distinguir homologia con hospedero,
  localizacion, virulencia o esencialidad;
- la subcapa evolutiva no tiene variables explicitas y solo puede derivarse con
  baja confianza.

Datos insuficientes no equivalen a bajo riesgo, ausencia biologica, evidencia
negativa ni irrelevancia terapeutica. Solo indican que la evidencia disponible
no alcanza para interpretar el ranking con confianza.

## Cierre esperado

Una validacion `user_curated` queda lista para revision si entrega:

- lista de archivos de usuario usados;
- organismo, cepa y alcance taxonomico;
- resumen de procedencia por capa;
- comando de importacion o preparacion;
- comando de pipeline usado;
- pruebas offline `not online` pasando;
- explicacion de faltantes y proxies;
- conclusion clara: ranking real producido, ranking exploratorio por datos
  parciales o datos insuficientes.
