# Plan de integracion de datos para Corynebacterium pseudotuberculosis biovar ovis

Este plan prepara una corrida real y trazable para aislados mexicanos de
`Corynebacterium pseudotuberculosis biovar ovis`, con ATCC 19410 como referencia
cuando aplique. No contiene datos biologicos inventados.

## Datos reales necesarios

- Identificadores consistentes de proteina, locus tag o gen.
- Esencialidad observada o inferida desde fuente trazable.
- Virulencia curada o derivada de viruloma reproducible.
- Homologia frente a humano u hospedero relevante.
- Localizacion subcelular.
- Conservacion entre aislados mexicanos y referencia.
- Red funcional o asociaciones funcionales reproducibles.
- Contexto clinico/infeccion y sitio terapeutico cuando exista evidencia.
- Soporte bibliografico manualmente curado.

## Posibles fuentes

- Pangenoma de aislados mexicanos y ATCC 19410.
- Anotacion funcional reproducible del genoma de referencia.
- Viruloma y resistoma generados por herramientas documentadas.
- Analisis de ortologia/homologia contra humano y, si aplica, hospedero.
- Predictores o anotaciones de localizacion con version registrada.
- Redes funcionales externas cacheadas o redes calculadas desde datos propios.
- Literatura curada manualmente con DOI, URL o cita verificable.

## Archivos que debe llenar el usuario

Las plantillas estan en:

`data_user/cpseudotuberculosis_biovar_ovis/templates/`

Archivos principales:

- `essentiality.csv`
- `virulence.csv`
- `human_homologs.csv`
- `localization.csv`
- `strain_conservation.csv`
- `functional_network.csv`
- `clinical_impact.csv`
- `curated_disease_context.csv`
- `therapy_site_context.csv`
- `literature_support.csv`
- `host_annotation.csv`

## Columnas obligatorias y opcionales

Las columnas obligatorias son los encabezados minimos de cada plantilla. En
general:

- `protein_id`: identificador estable usado por el pipeline.
- `gene`: simbolo o nombre del gen, si existe.
- columnas numericas especificas de cada capa, acotadas entre 0.0 y 1.0 cuando
  representen scores o fracciones.
- `database`: etiqueta de procedencia recomendada para trazabilidad.

`literature_support.csv` incluye campos adicionales como `reference`,
`doi_or_url`, `notes` y `source_quality`.

## Conversion de resultados bioinformaticos

- Pangenoma: convertir presencia por aislado a `core_genome_presence` y
  `strain_coverage_score`; documentar numero total de cepas.
- Variacion alelica: usar `allelic_conservation` y `variant_burden` solo si el
  analisis de variantes es reproducible; si no, dejar vacio.
- Viruloma: mapear genes confirmados a `virulence_factor=1` y un
  `virulence_score` justificado; no asignar puntuaciones altas solo por
  similitud debil.
- Resistoma/tolerancia: no existe capa directa en el scoring actual; usar notas
  en `literature_support.csv` o en plantillas de validacion biologica.
- Red funcional: convertir centralidad, bottleneck, redundancia y dependencia a
  escalas 0.0-1.0; documentar algoritmo y version.
- Localizacion: usar vocabulario permitido por `config/params.yaml`.
- Homologia: documentar metodo, base, e-value y criterio de corte.

## Datos que no deben inferirse sin evidencia

- Esencialidad experimental.
- Virulencia confirmada in vivo.
- Conservacion alelica si no hay analisis de variantes.
- Impacto clinico o dano al hospedero si solo hay inferencias internas.
- Ausencia de riesgo en hospedero sin busqueda de homologia/ortologia.
- Soporte bibliografico sin referencia verificable.

## Marcado de procedencia

Usa valores de `database` expresivos, por ejemplo:

- `user_curated_cpseudo_ovis_pangenome_v1`
- `user_curated_cpseudo_ovis_virulome_v1`
- `computed_from_user_pangenome_v1`
- `external_real_cache_bvbrc_v1`
- `pending_manual_curation`

Evita marcar como curado un dato que venga de demo, proxy o regla controlada.

## Dry-run

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --strain "biovar ovis" --acquisition-mode semi_auto --workspace data_sessions\cpseudo_mexico --dry-run
```

El dry-run prepara discovery, perfil del organismo, manifest de adquisicion y
reporte, sin ejecutar el motor de scoring.

## Corrida real

Cuando los CSV esten llenos y revisados:

1. Copiar los archivos curados al workspace, preferentemente en
   `data_sessions/cpseudo_mexico/data_user/` o en el esquema que use el
   resolvedor.
2. Verificar que las columnas coincidan con las plantillas.
3. Ejecutar una corrida sin `--dry-run`.

Ejemplo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --strain "biovar ovis" --acquisition-mode semi_auto --workspace data_sessions\cpseudo_mexico --mode compare
```

## Advertencias cientificas

- El ranking es una priorizacion computacional exploratoria.
- No confirma eficacia terapeutica ni reemplaza validacion experimental.
- La fuerza de cada candidato depende de procedencia, especificidad,
  trazabilidad y cobertura de capas.
- Los campos derivados, proxy o controlados deben marcarse como tales.
- Las conclusiones biologicas finales requieren curacion manual y evidencia
  experimental o bibliografica verificable.
