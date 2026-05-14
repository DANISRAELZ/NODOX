# Nodos Funcionales

Nodos Funcionales es una plataforma bioinformatica multiorganismo para la
priorizacion explicable de blancos terapeuticos bacterianos. El sistema permite
que el usuario ingrese informacion genomica, funcional, clinica o curada de
cualquier organismo bacteriano, y combina esta evidencia con fuentes externas,
catalogos, redes funcionales y modelos de puntuacion multicapa para identificar
candidatos terapeuticos con potencial antibacteriano, antivirulencia,
sensibilizador o de nodo funcional. La plataforma incorpora auditoria de
procedencia, evaluacion de confiabilidad, clasificacion del rol terapeutico y
estimacion progresiva del riesgo evolutivo de escape, permitiendo generar
rankings interpretables y comparables entre organismos.

Los organismos mencionados en ejemplos, cache o pruebas son demos/casos de
validacion; no son organismos obligatorios ni el alcance exclusivo del sistema.

## Enfoque conceptual

El eje central de este proyecto es la Teoria de Nodos Funcionales. El pipeline,
los organismos ejemplo, la consulta online, los snapshots curados, los
importadores, las pruebas y los reportes son capas de implementacion destinadas
a operacionalizar, probar y auditar la teoria. Ningun organismo, base de datos,
conector o conjunto de datos define por si mismo el alcance conceptual del
proyecto.

Pipeline reproducible para priorización de blancos terapéuticos bacterianos.

El repositorio conserva la **Fase 1** como baseline interpretable y añade una
**Fase 2** multicapa con validación más estricta, variables derivadas,
scores por estrategia terapéutica, análisis de sensibilidad, modos explícitos
de ejecución y salidas auditables.

Además, ahora incorpora una **capa de discovery por microorganismo** para que el
usuario pueda iniciar el flujo desde el nombre del organismo y, opcionalmente, una cepa.

## Quick start

Instalacion en Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ejecutar el demo de `Pseudomonas aeruginosa` PAO1:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Este comando usa PAO1 unicamente como organismo demo reproducible. Para analisis
reales, reemplace `--organism` y `--strain` por el organismo y cepa de interes y
proporcione datos curados, importados o resueltos por las capas configuradas.

Consultar informacion online general para `Corynebacterium pseudotuberculosis`:

```powershell
python fetch_online_data.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --sources uniprot string --mode online_optional --force-refresh
```

Ejemplos multiorganismo, todos ilustrativos:

```powershell
python run_pipeline.py --organism "Organism name" --strain "Strain name" --mode compare
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
python run_pipeline.py --organism "Mycobacterium tuberculosis" --strain H37Rv --workspace data_sessions/mtb_h37rv --mode compare
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions/corynebacterium_pseudotuberculosis_online_demo --mode compare
python import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_NAME" --workspace data_sessions/my_organism_workspace --dataset essentiality --input-dir path/to/user_data
```

Estos comandos muestran patrones de uso. Ningun organismo de ejemplo es requisito
del programa.

Ejecutar pruebas:

```powershell
python -m pytest -q
```

## Estado de madurez del proyecto

Nodos Funcionales es un prototipo cientifico avanzado orientado a
priorizacion computacional exploratoria. Ya incluye resolucion de capas,
procedencia, reportes interpretativos, auditoria de fuentes, plantillas de
curacion y soporte para workspaces por organismo. No debe leerse como una
herramienta de validacion terapeutica definitiva.

El ranking generado por Nodos Funcionales debe interpretarse como priorizacion
computacional exploratoria. No confirma eficacia terapeutica ni reemplaza
validacion experimental.

## Tipos de datos de entrada

Las capas principales son `essentiality`, `virulence`, `human_homologs`,
`localization`, `strain_conservation`, `functional_network`,
`clinical_impact`, `curated_disease_context` y `therapy_site_context`.
Cada archivo debe respetar los encabezados de `data_templates/`.

La capa opcional `literature_support` permite preparar curacion bibliografica
manual. Por defecto se valida y normaliza si existe, se reporta como evidencia
interpretativa en `results/literature_support_summary.*` y no cambia los
scores ni el ranking.

## Demo, datos reales, cache y proxy

- `data_demo/`: datos pequenos para probar el software; no son evidencia
  biologica final.
- datos reales de usuario: deben colocarse en el workspace o importarse segun
  las instrucciones de adquisicion.
- cache: reproduce consultas o capas ya resueltas.
- proxy: valor explicito usado cuando falta una capa; sirve para mantener el
  flujo, pero reduce la fuerza interpretativa.

## Auditoría de procedencia de capas

El proyecto no asume que todas las capas vienen de bases externas reales ni que
una fuente externa siempre es metodologicamente superior. Cada capa puede venir
de datos curados por el usuario, evidencia especifica del organismo, archivos
locales, cache, fuentes externas reales, fuentes externas generales, datos demo,
valores proxy, proveedores controlados o literatura curada manualmente.

La auditoria completa esta en:

- `docs/layer_source_audit.md`
- `docs/layer_source_audit.json`
- `docs/layer_source_summary.csv`
- `docs/project_scope.md`
- `docs/multiorganism_architecture.md`
- `docs/user_data_input_guide.md`
- `docs/organism_reference_audit.md`

Jerarquia metodologica recomendada:

1. Evidencia curada por el usuario, especifica del organismo y trazable.
2. Evidencia externa real, verificable y preferentemente cacheada.
3. Evidencia calculada internamente desde datos del usuario.
4. Evidencia local/raw.
5. Evidencia externa general no especifica.
6. Evidencia proxy o proveedor controlado.
7. Datos demo.

El ranking debe interpretarse como priorizacion computacional exploratoria. La
fuerza de cada candidato depende de la procedencia, calidad, especificidad,
trazabilidad y cobertura de las capas de evidencia.

## Como interpretar los scores

Los scores son una priorizacion computacional exploratoria. Un valor alto no
confirma eficacia terapeutica, seguridad, accesibilidad real ni validez clinica.
El ranking ayuda a ordenar hipotesis y a decidir que evidencia falta revisar o
generar experimentalmente.

Antes de concluir que un blanco es prometedor, revisar:

- esencialidad y virulencia.
- riesgo por homologos humanos.
- conservacion entre cepas.
- localizacion y accesibilidad.
- soporte funcional de red.
- procedencia de la evidencia: real, demo, cache, proxy o calculo indirecto.

## Uso exploratorio

Nodos Funcionales no reemplaza validacion experimental ni revision
bibliografica. Los candidatos priorizados deben interpretarse segun calidad,
cobertura y procedencia de evidencia. Los datos demo o proxy no deben usarse
para conclusiones biologicas finales.

## Ejemplo generico con Corynebacterium pseudotuberculosis

Corynebacterium pseudotuberculosis puede usarse como organismo de ejemplo para validar el flujo multi-organismo y la consulta online. Este ejemplo no corresponde a una coleccion particular de aislados ni a un proyecto genomico externo.

Para preparar una corrida inicial sin ejecutar scoring:

```powershell
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --acquisition-mode semi_auto --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --dry-run
```

Luego revisar los archivos esperados en el reporte de discovery, completar datos reales en el workspace si se desea una corrida completa y ejecutar el pipeline cuando las capas obligatorias esten listas.

La consulta online organism-first se documenta en `docs/online_organism_enrichment.md`.

## Fuerza de evidencia

El proyecto separa el score numerico de la fuerza interpretativa de la
evidencia. El reporte `results/evidence_strength_audit.csv` clasifica evidencia
como `strong`, `moderate`, `weak` o `insufficient` sin modificar el ranking.

Ver `docs/evidence_strength_framework.md`.

## Ejecucion en Windows

Si `python` no esta en `PATH`, usa los scripts PowerShell:

- `scripts/run_tests.ps1`
- `scripts/run_demo.ps1`
- `scripts/run_cpseudo_dryrun.ps1`
- `scripts/clean_project.ps1`

La guia completa esta en `docs/windows_execution_guide.md`.

## Validacion biologica

La validacion biologica se organiza con:

- `docs/biological_validation_framework.md`
- `docs/biological_validation_summary_template.md`
- `data_templates/biological_validation_targets.csv`

Estos archivos ayudan a curar evidencia, planear experimentos y degradar
candidatos con soporte debil, pero no alteran scores.

## Diferencia entre Fase 1 y Fase 2

- Fase 1:
  score lineal único basado en esencialidad, virulencia, homología humana y accesibilidad.
- Fase 2:
  separa estrategias terapéuticas, distingue faltante vs negativo, añade confianza
  de evidencia, refina riesgo del hospedero, prepara arquitectura para red,
  conservación e impacto clínico, y genera comparación explícita con el baseline.

## Phase 3: Functional Node Theory and Evolutionary Robustness

La Fase 3 ya esta implementada como una capa opcional y funcional. No reemplaza
Fase 1 ni Fase 2: conserva los scores previos para comparacion y agrega una
lectura adicional de teoria de nodos funcionales, escape evolutivo, redundancia,
sensibilidad colateral, oportunidad de combinacion y calidad de evidencia.

La Fase 3 debe interpretarse como una priorizacion computacional exploratoria.
Su madurez cientifica depende directamente de la calidad de las capas de entrada.
Si se ejecuta con datos demo, proveedores controlados o defaults inferidos, los
reportes lo marcan en `audit_flags` y limitan la confianza mediante
`confidence_ceiling`.

Para ejecutar la salida completa de Fase 3:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode phase3
```

PAO1 se conserva aqui como caso demostrativo/controlado para reproducir salidas.
El flujo no esta acoplado a PAO1; para organismos reales use los nombres de su
organismo y cepa y revise la procedencia de cada capa.

Para comparar que Fase 1/Fase 2 siguen funcionando:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Reportes principales de Fase 3:

- `results/theory_of_nodes_report.md`
- `results/evolutionary_escape_audit.csv`
- `results/top10_functional_node_theory_audit.md`
- `results/therapeutic_role_stability_audit.csv`
- `results/therapeutic_role_stability_report.md`
- `results/ranking_nodos_phase3.csv`
- `results/phase2_vs_phase3_comparison.csv`
- `data_processed/phase3_features.csv`
- `data_processed/scored_nodes_phase3.csv`
- `results/phase3_implementation_audit.md`

Durante la ejecucion por CLI, Fase 3 informa cuando calcula escape evolutivo,
cuando calcula el score de Teoria de Nodos Funcionales y donde escribe el
ranking. Si se usan datos demo con `--allow-demo-data`, la salida advierte que
la confianza queda limitada.

### Como interpretar `meta_priority_score_v3`

`meta_priority_score_v3` combina soporte antibiotico, soporte antivirulencia,
`functional_node_theory_score`, calidad de evidencia y oportunidad de
combinacion. Tambien descuenta riesgo de escape, redundancia, biofilm y
transferencia horizontal.

Un valor alto no confirma eficacia terapeutica. Significa que, bajo las reglas
actuales y la evidencia disponible, el nodo merece revision prioritaria. Siempre
debe leerse junto con:

- `functional_node_theory_score`
- `functional_node_theory_confidence`
- `evolutionary_escape_risk_score`
- `redundancy_penalty`
- `evidence_quality_score`
- `confidence_ceiling`
- `audit_flags`

Advertencia importante: cuando `audit_flags` contiene `demo_data_used`,
`controlled_provider_only`, `*_defaults_used` o `*_inferred*`, la evidencia es
util para probar el pipeline o generar hipotesis, pero no para sostener una
conclusion biologica final.

### Entradas curadas para reemplazar demo/defaults

Fase 3 acepta evidencia curada por organismo sin hacerla obligatoria. Las
plantillas estan vacias salvo encabezados para evitar datos inventados:

- `data_templates/human_homologs_template.csv`: ahora acepta campos de
  ortologia reproducible como herramienta, version, cobertura, identidad,
  bitscore y referencia de corrida.
- `data_templates/redundancy_template.csv`: nueva capa opcional para paralogia,
  alternativas de via y backups funcionales.
- `data_templates/evolutionary_escape_template.csv`: ahora acepta mutaciones de
  escape conocidas, tolerancia funcional inferida, participacion modular y
  scores de rutas alternativas.
- `data_templates/collateral_sensitivity_template.csv`: ahora acepta clase de
  combinacion, pareja terapeutica, referencia y oportunidad de combinacion.

Ver `docs/phase3_curated_evidence_inputs.md`.

## Estructura del proyecto

```text
nodos/
├── config/
│   └── params.yaml
│   ├── taxon_aliases.json
│   └── demo_organisms.json
├── data_sessions/
│   └── <slug_microorganismo>/
│       ├── config/
│       ├── data_raw/
│       ├── data_processed/
│       └── results/
├── data_templates/
│   ├── strain_conservation_template.csv
│   ├── functional_network_template.csv
│   ├── host_annotation_template.csv
│   ├── essentiality_template.csv
│   ├── virulence_template.csv
│   ├── human_homologs_template.csv
│   └── localization_template.csv
├── data_raw/
│   ├── essentiality.csv
│   ├── strain_conservation.csv         # opcional
│   ├── functional_network.csv          # opcional
│   ├── host_annotation.csv             # opcional
│   ├── virulence.csv
│   ├── human_homologs.csv
│   └── localization.csv
├── data_processed/
│   ├── validated_*.csv
│   ├── normalized_*.csv
│   ├── integrated_nodes.csv
│   ├── validation_summary.csv
│   ├── phase2_features.csv
│   └── scored_nodes.csv
├── docs/
│   ├── methodology.md
│   ├── scoring.md
│   └── data_model.md
├── results/
│   ├── ranking_nodos.csv
│   ├── ranking_nodos_legacy.csv
│   ├── phase_comparison.csv
│   ├── sensitivity_analysis.csv
│   └── report_phase2.md
├── scripts/
│   ├── 01_load_and_validate.py
│   ├── 02_normalize_ids.py
│   ├── 03_integrate_data.py
│   ├── 04_score_nodes.py
│   └── 05_export_ranking.py
├── src/
│   └── nodos_funcionales/
├── tests/
├── Snakefile
├── run_pipeline.py
└── requirements.txt
```

## Nuevo flujo centrado en microorganismo

El proyecto ahora tiene dos puertas de entrada complementarias:

- flujo clásico:
  colocar CSVs en `data_raw/` y correr `scripts/01..05`
- flujo discovery-driven:
  iniciar con `run_pipeline.py --organism ...` y dejar que el sistema genere
  el workspace, el perfil del organismo y el manifest de adquisición

Además, ahora existe una primera integración online opcional para enriquecer
la capa de red funcional mediante **STRING**.

Ejemplos:

```bash
python run_pipeline.py --organism "Organism name" --strain "Strain name" --workspace data_sessions/my_organism_workspace --mode compare
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --dry-run
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data
python run_pipeline.py --organism "Mycobacterium tuberculosis" --acquisition-mode semi_auto --mode compare
python run_pipeline.py --organism "Mycobacterium tuberculosis" --strain H37Rv --taxon-resolution-mode cache_first --dry-run
python run_pipeline.py --organism "Pseudomonas aeruginosa" --taxon-resolution-mode online_optional --refresh-taxon-cache --dry-run
```

## Modos de adquisición

Los nombres concretos son ejemplos reproducibles o casos de validacion. El
usuario puede proporcionar cualquier organismo bacteriano compatible con las
capas de evidencia disponibles.

- `manual`:
  crea o reutiliza el workspace y espera que el usuario coloque los CSVs
- `semi_auto`:
  crea el workspace, genera plantillas y un checklist reproducible
- `auto`:
  hoy es una arquitectura preparada; si existe un demo local compatible puede usarlo,
  pero no simula APIs reales ni descargas externas inexistentes

## Qué hace el discovery layer

La nueva capa:

- resuelve el nombre del microorganismo con un catálogo local configurable
- puede consultar opcionalmente una API taxonómica pública real con fallback seguro
- preserva el nombre original y produce un nombre canónico interno
- crea un workspace en `data_sessions/<slug>/`
- clasifica datasets obligatorios, opcionales enriquecedores y futuros
- genera `organism_profile.json`, `acquisition_manifest.json` y `discovery_report.md`
- indica explícitamente si el pipeline puede correr ya o qué falta

## Datasets mínimos que necesita el motor

Obligatorios:

- `essentiality.csv`
- `virulence.csv`
- `human_homologs.csv`
- `localization.csv`

Opcionales enriquecedores:

- `strain_conservation.csv`
- `functional_network.csv`
- `host_annotation.csv`

Futuros:

- `clinical_impact.csv`
- `curated_disease_context.csv`
- `therapy_site_context.csv`

## Inputs esperados

Todos los archivos van en `data_raw/` y deben contener al menos `protein_id`.

- `essentiality.csv`: `protein_id`, `gene`, `essential`, opcionalmente `evidence`, `database`
- `virulence.csv`: `protein_id`, `gene`, `virulence_score`, opcionalmente `virulence_factor`, `database`
- `human_homologs.csv`: `protein_id`, `gene`, `human_homolog`, `evalue`, opcionalmente `human_gene`
- `localization.csv`: `protein_id`, `gene`, `localization`, opcionalmente `database`
- `strain_conservation.csv` opcional: `protein_id`, `gene`, `core_genome_presence`, `strain_coverage_score`, `allelic_conservation`, `variant_burden`, opcionalmente `database`
- `functional_network.csv` opcional: `protein_id`, `gene`, `network_centrality`, `pathway_bottleneck_score`, `redundancy_penalty`, `functional_dependency_score`, opcionalmente `database`
- `host_annotation.csv` opcional: `protein_id`, `gene`, `domain_overlap_score`, `host_criticality_penalty`, opcionalmente `database`

El repositorio incluye tablas opcionales de ejemplo con origen `example_curated_demo`.
Sirven para demostrar la arquitectura de Fase 2 y no deben leerse como una validación
biológica exhaustiva.

Si dispones de datos curados reales, puedes reemplazar esas tablas manteniendo el mismo
esquema y declarando una procedencia más informativa en la columna `database`, por ejemplo:

- `curated_pangenome_pa14_v1`
- `lit_string_network_pa01_v2`
- `exp_host_domain_overlap_2026`

## Qué valida el pipeline

La validación ya no se limita a columnas presentes. También revisa:

- archivos vacíos
- `protein_id` vacíos
- duplicados
- tipos numéricos
- rangos válidos
- localizaciones permitidas
- inconsistencias semánticas básicas
- resumen de faltantes por columna

El reporte queda en `data_processed/validation_summary.csv`.

## Cómo correr el pipeline

### Opción recomendada: paso a paso

```bash
python scripts/01_load_and_validate.py
python scripts/02_normalize_ids.py
python scripts/03_integrate_data.py
python scripts/04_score_nodes.py --mode compare
python scripts/05_export_ranking.py --mode compare
```

Modos disponibles para `scripts/04_score_nodes.py` y `scripts/05_export_ranking.py`:

- `--mode default`: alias conservador de `compare`
- `--mode legacy`: ranking principal igual al baseline Fase 1
- `--mode phase2`: ranking principal igual a `meta_priority_score`
- `--mode phase3`: ejecuta Fase 2 y agrega las capas opcionales de Fase 3,
  `meta_priority_score_v3`, ranking Fase 3 y reportes cientificos
- `--mode compare`: ranking principal Fase 2 más comparación explícita con legacy

### Con Snakemake

```bash
snakemake --dry-run
snakemake --cores 1
```

El `Snakefile` usa el mismo intérprete de Python que ejecuta Snakemake, para evitar
problemas de PATH entre entornos.

### Con discovery por microorganismo

`run_pipeline.py` genera un workspace de organismo y, si hay datos suficientes,
llama internamente al motor actual.

Flags principales:

- `--organism`
- `--strain`
- `--strategy`
- `--acquisition-mode`
- `--taxon-resolution-mode`
- `--online-source-mode`
- `--refresh-taxon-cache`
- `--no-write-taxon-cache`
- `--offline-only`
- `--mode`
- `--workspace`
- `--allow-demo-data`
- `--dry-run`

Para una ejecucion completamente offline/cache segura, use:

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

Este ejemplo usa PAO1 solo como demo offline controlado. Para un analisis nuevo,
reemplace el organismo/cepa y prepare un workspace con datos propios o fuentes
externas permitidas.

`--taxon-resolution-mode` controla solo la resolucion taxonomica. `--online-source-mode`
controla las fuentes externas de capas como `human_homologs`, `functional_network`,
`localization` y `host_annotation`. Por seguridad, `--offline-only`,
`--taxon-resolution-mode offline_only`, `local` y `api_stub` fuerzan
`online_source_mode=offline_only` para todo el pipeline.

### Con enriquecimiento online opcional

La primera fuente online conectada es **STRING**, elegida antes que UniProt
porque fortalece directamente una capa ya existente y metodológicamente débil
del modelo actual: `functional_network.csv`.

Ejemplo:

```bash
python fetch_online_data.py --organism "Pseudomonas aeruginosa" --workspace data_sessions/pao1_demo --source string --mode online_optional
```

PAO1 se muestra aqui como ejemplo reproducible de enriquecimiento. El mismo
patron aplica a otros organismos cuando la fuente externa y la configuracion de
resolucion lo permiten.

Modos soportados:

- `offline_only`
- `local`
- `api_stub`
- `cache_first`
- `auto`
- `online_optional`

Solo `online_optional` puede abrir red. `offline_only`, `local` y `api_stub`
no llaman UniProt, STRING, DEG, VFDB, BV-BRC, InterPro ni ningun proveedor
basado en `urllib.request.urlopen`.

El enriquecimiento:

- usa caché local reproducible por workspace
- puede funcionar sin red si ya existe caché
- genera `results/online_source_manifest.json`
- genera `results/online_source_report.md`
- toma un snapshot previo del ranking cuando el workspace ya tiene resultados
- reejecuta el pipeline del workspace por defecto tras el fetch
- genera `results/online_enrichment_impact.csv` y `.md` con comparación antes/después si existe un ranking previo
- guarda histórico por workspace en `results/online_source_history.jsonl`
- genera `results/online_source_comparison.csv` y `.md` para comparar fuentes online dentro del workspace
- permite auditoría limpia por fuente en workspaces clonados con `audit_online_sources.py`
- puede escribir `data_raw/functional_network.csv` si el reemplazo es seguro

Ejemplo de auditoría fresh/cache:

```bash
python audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions/pao1_demo --sources string uniprot --compare-fresh-vs-cache
```

La auditoria anterior es un caso de validacion controlada, no el organismo base
del proyecto.

Nota:

- `--force-refresh` sirve para corridas online frescas, pero no debe combinarse con `--compare-fresh-vs-cache` porque invalidaría el control basado en caché

Modos taxonómicos soportados:

- `offline_only`
- `cache_first`
- `online_optional`
- `api_stub`
- `auto`

Compatibilidad hacia atrás:

- `local` sigue aceptado como alias de `offline_only`

## Importación semiautomática de exports del usuario

Además del discovery, ahora existe un importador pragmático para convertir CSVs
exportados por el usuario al esquema interno del workspace:

```bash
python import_dataset.py --workspace data_sessions/organism_demo --dataset virulence --input exported_virulence.csv
```

El importador:

- conserva una copia del export original en `data_raw/source_exports/`
- intenta mapear columnas frecuentes como `locus_tag -> protein_id` o `score -> virulence_score`
- escribe el dataset interno listo para validación en `data_raw/`

## Comparación entre workspaces

También existe un comparador de sesiones discovery-driven:

```bash
python compare_workspaces.py
```

Genera:

- `results/workspace_comparison.csv`
- `results/workspace_comparison.md`

Ahora también resume, cuando existe un enriquecimiento online previo:

- fuente online usada
- cache hit / miss
- éxito de API en la corrida actual
- si el enriquecimiento cambió el ranking o solo añadió anotación/procedencia
- cuántas corridas online tiene el workspace y qué fuentes se usaron

## Salidas principales

- `data_processed/integrated_nodes.csv`: tabla maestra integrada
- `data_processed/phase2_features.csv`: features derivadas y flags de placeholder
- `data_processed/scored_nodes.csv`: scores legacy y de Fase 2 por proteína
- `results/ranking_nodos.csv`: ranking principal Fase 2 con rol terapeutico, procedencia y descomposicion de `therapeutic_priority_score`
- `results/ranking_nodos_legacy.csv`: baseline Fase 1
- `results/phase_comparison.csv`: comparación de ranking Fase 1 vs Fase 2
- `results/sensitivity_analysis.csv`: escenarios de sensibilidad
- `results/report_phase2.md`: resumen interpretable
- `results/data_provenance_summary.csv`: procedencia y calidad de datasets opcionales
- `results/candidate_audit.csv`: auditoría por candidato
- `results/candidate_audit.md`: auditoría por candidato en formato legible
- `results/top10_candidate_review.csv`: revisión priorizada del top 10
- `results/top10_candidate_review.md`: revisión priorizada del top 10 en Markdown
- `results/top10_scientific_audit.csv`: auditoría científica estricta del top 10
- `results/top10_scientific_audit.md`: lectura biológica y metodológica del top 10
- `results/top10_scientific_summary.md`: resumen corto de la auditoría científica
- `results/online_source_manifest.json`: trazabilidad del enriquecimiento online
- `results/online_source_report.md`: resumen legible de lo recuperado desde la fuente online
- `results/online_enrichment_impact.csv`: comparación antes/después del ranking tras enriquecer el workspace
- `results/online_enrichment_impact.md`: resumen legible del impacto del enriquecimiento online
- `results/online_source_history.jsonl`: histórico append-only de enriquecimientos online por workspace
- `results/online_source_comparison.csv`: comparación de fuentes online usadas dentro del workspace
- `results/online_source_comparison.md`: resumen legible de comparación entre fuentes online del workspace
- `results/online_source_clean_audit.csv`: comparación limpia por fuente usando clones temporales del workspace
- `results/online_source_clean_audit.md`: resumen legible de la comparación limpia por fuente
- `results/online_source_fresh_audit.csv`: auditoría experimental por escenarios fresh/cache
- `results/online_source_fresh_audit.md`: resumen legible de la auditoría experimental fresh/cache
- `results/online_source_fresh_vs_cache.csv`: contraste directo entre escenarios fresh y cache
- `results/online_source_fresh_vs_cache.md`: resumen legible del contraste fresh vs cache
- `results/online_source_candidate_shifts_fresh.csv`: shifts de ranking por candidato en la auditoría fresh/cache
- `results/workspace_comparison.csv`: comparación entre workspaces
- `results/workspace_comparison.md`: comparación entre workspaces en Markdown
- `results/theory_of_nodes_report.md`: reporte cientifico de Fase 3 con top candidatos, subidas/bajadas y advertencias
- `results/evolutionary_escape_audit.csv`: auditoria evolutiva por nodo para Fase 3
- `results/evolutionary_escape_risk_audit.csv`: auditoria de la subcapa `evolutionary_escape_risk`, variables faltantes, confianza y penalizacion aplicada
- `results/top10_functional_node_theory_audit.md`: explicacion detallada de los mejores candidatos por teoria de nodos
- `results/therapeutic_role_stability_audit.csv`: auditoria de estabilidad del rol terapeutico v2/v3
- `results/therapeutic_role_stability_report.md`: resumen legible de estabilidad del rol terapeutico
- `results/ranking_nodos_phase3.csv`: ranking opcional Fase 3
- `results/phase2_vs_phase3_comparison.csv`: comparacion entre ranking Fase 2 y Fase 3
- `results/phase3_implementation_audit.md`: auditoria final de implementacion y madurez de Fase 3
- `data_processed/phase3_features.csv`: features completas de Fase 3
- `data_processed/scored_nodes_phase3.csv`: tabla compacta de scores de Fase 3

Dentro de cada workspace discovery-driven también se generan:

- `results/organism_profile.json`
- `results/acquisition_manifest.json`
- `results/discovery_report.md`

## Scores implementados

- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `therapeutic_priority_score`
- `evolutionary_escape_risk_score`
- `evolutionary_adjusted_meta_priority_score`

## Explicabilidad por candidato

Las salidas incluyen columnas como:

- `top_positive_drivers`
- `top_negative_drivers`
- `missing_evidence_flags`
- `confidence_summary`
- `evidence_confidence_score`
- `evidence_coverage_score`
- `functional_node_types`
- `therapeutic_priority_contribution_summary`
- `therapeutic_priority_*_contribution`
- `provenance_status`
- `retrieval_mode`
- `cache_status`

Además, la Fase 2 ya usa datos observados o proxies explícitas cuando están disponibles:

- `domain_overlap_score` y `host_criticality_penalty` desde `host_annotation.csv` si existe, con fallback derivado de homología humana
- `core_genome_presence`, `strain_coverage_score`, `allelic_conservation` y `variant_burden` desde `strain_conservation.csv`
- `network_centrality`, `pathway_bottleneck_score`, `redundancy_penalty` y `functional_dependency_score` desde `functional_network.csv`
- `infection_site_access` a partir de localización subcelular
- `host_damage_reduction_potential` como proxy basada en virulencia y accesibilidad
- `disease_severity_association` como proxy basada en señal de virulencia
- `clinical_impact_score` como proxy derivada de impacto y acceso

## Configuración editable

El comportamiento del pipeline se controla desde `config/params.yaml`.
Ahí puedes ajustar:

- pesos legacy y Fase 2
- `runtime.pipeline_mode`
- reglas de procedencia y calidad de fuentes en `provenance`
- reglas por localización subcelular
- defaults neutros para desconocido
- placeholders para variables futuras
- pesos y penalizacion de `evolutionary_escape_risk`
- escenarios de sensibilidad para `meta_priority_score` y para cada score estratégico
- umbrales globales

### Riesgo de escape evolutivo

La subcapa `evolutionary_escape_risk` agrega una lectura explicita de riesgo de
resistencia o escape frente a un candidato. Usa datos curados si existe
`evolutionary_escape_risk.csv`; si no, deriva proxies auditables desde capas ya
resueltas y baja la confianza cuando la evidencia explicita es escasa.

`evolutionary_escape_risk_score` va de 0 a 1: valores altos significan mayor
riesgo de escape. El pipeline conserva `meta_priority_score` y agrega
`evolutionary_adjusted_meta_priority_score`, que aplica por defecto una
penalizacion moderada de hasta 15%. Los datos demo se marcan como
`source_type=demo` y no deben interpretarse como evidencia biologica real.

## Tests

El repositorio incluye pruebas mínimas para validación, integración,
scoring, exportación y un flujo end-to-end con datos de ejemplo.

```bash
python -m unittest discover -s tests -v
```

## Limitaciones actuales

- La resolución taxonómica online es opcional y depende de conectividad real.
- Si la API pública falla, el sistema degrada a caché o catálogo local y lo deja
  explícito en `taxon_resolution_status`, `source_used`, `api_attempted` y `fallback_reason`.
- La resolución taxonómica no debe interpretarse como validación de cepa cuando el
  proveedor solo devuelve un taxón a nivel de especie.
- La integración con STRING produce métricas de red **derivadas** a partir del grafo
  recuperado; no deben interpretarse como mediciones experimentales directas.
- Si STRING devuelve nombres preferidos inconsistentes con la columna `gene` local,
  el manifest lo marca explícitamente; eso puede revelar problemas de mapeo o
  inconsistencias previas en los datos del workspace.
- `auto` no implementa adquisición real online. Solo prepara arquitectura y puede usar
  un demo empaquetado cuando el organismo coincide exactamente con el ejemplo local.
- Las capas de conservación, red funcional y anotación de hospedero ya aceptan
  datos observados, pero el ejemplo incluido sigue siendo un dataset curado pequeño.
- El pipeline ahora descuenta parcialmente la confianza de Fase 2 cuando las capas
  opcionales provienen de fuentes marcadas como `demo`; eso mejora la honestidad
  metodológica, pero no sustituye una curación biológica real.
- Mientras las capas opcionales sigan como `demo_only`, el `meta_priority_score`
  favorece un poco más la señal antibiótica y reduce la dependencia del score
  funcional en la integración final.
- `host_damage_reduction_potential`, `disease_severity_association` y `clinical_impact_score`
  ya no son placeholders, pero siguen siendo **proxies derivadas** de la evidencia
  disponible; no sustituyen una medición clínica o experimental directa.
- El `functional_node_score` mejora cuando hay red funcional real, pero sigue siendo
  metodológicamente sensible a cómo se definan centralidad, cuello de botella y redundancia.

## Roadmap sugerido

- conectar matrices de homología/dominios para refinar seguridad del hospedero
- incorporar datos reales de centralidad/red y redundancia funcional
- añadir conservación multi-cepa o pangenoma
- integrar severidad clínica y reducción de daño al hospedero
- sumar exportación HTML si se necesita un reporte más visual

## Documentación adicional

- [Metodología](docs/methodology.md)
- [Scoring](docs/scoring.md)
- [Modelo de datos](docs/data_model.md)
- [Auditoría metodológica](docs/audit_scoring.md)
- [Ingesta de datos reales](docs/real_data_ingestion.md)
- [Discovery layer](docs/discovery_layer.md)
- [Acquisition modes](docs/acquisition_modes.md)
- [Organism workflow](docs/organism_workflow.md)
- [Taxonomy resolution](docs/taxonomy_resolution.md)
- [Taxonomy API integration](docs/taxonomy_api_integration.md)
- [Taxon cache policy](docs/taxon_cache_policy.md)
- [Online source integration](docs/online_source_integration.md)
- [Online source fresh audit](docs/online_source_fresh_audit.md)
- [Source cache policy](docs/source_cache_policy.md)
- [Therapeutic expansion phase 1](docs/therapeutic_expansion_phase1.md)
- [Theory of Functional Nodes](docs/theory_of_functional_nodes.md)
- [Evolutionary escape model](docs/evolutionary_escape_model.md)
- [Contextual essentiality](docs/contextual_essentiality.md)
- [Redundancy and compensation](docs/redundancy_and_compensation.md)
- [Collateral sensitivity](docs/collateral_sensitivity.md)
- [Phase 3 scoring](docs/phase3_scoring.md)
- [Dataset import](docs/dataset_import.md)
- [Workspace comparison](docs/workspace_comparison.md)
