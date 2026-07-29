# Capa de homologia humana por DIAMOND

## Proposito cientifico

Esta fase cambia la capa `human_homologs` hacia una evidencia reproducible basada en alineamiento proteico. El objetivo es evitar que coincidencias por nombre de gen o nombre de proteina se interpreten como homologia humana real sin metricas de secuencia.

`human_homolog` representa una senal conservadora de similitud u homologia humana detectable bajo parametros definidos. No es una validacion toxicológica ni una prueba clinica de riesgo al hospedero.

## Variables nuevas o reforzadas

- `human_homolog`: 1 solo para homologia fuerte o similitud parcial significativa por alineamiento; 0 para busqueda valida sin similitud detectable; vacio para evidencia no resuelta.
- `homology_evidence_tier`: categoria interpretable de evidencia.
- `percent_identity`, `query_coverage`, `subject_coverage`, `evalue`, `bit_score`: metricas directas del mejor hit DIAMOND.
- `orthology_tool`, `orthology_version`, `orthology_reference`: trazabilidad del metodo.
- `homology_evidence_note`: nota metodologica, incluyendo umbral, sensibilidad, proteoma de referencia y advertencias.

## Reglas de scoring y clasificacion

- `strong_human_sequence_homology`: `evalue <= 1e-10`, identidad >= 25%, query coverage >= 0.50 y subject coverage >= 0.50.
- `partial_human_sequence_similarity`: `evalue <= 1e-5`, identidad >= 20% y query coverage >= 0.20, sin cumplir todos los criterios fuertes.
- `weak_low_coverage_similarity`: existe hit, pero no cumple los criterios anteriores; por defecto queda no resuelto para `human_homolog`.
- `no_detectable_human_similarity`: no existe hit al umbral usado; se codifica como `human_homolog = 0` solo si la busqueda fue valida.
- `name_match_unverified`: coincidencia por nombre o simbolo sin metricas de alineamiento; no eleva `human_homolog`.

La frase correcta para negativos es: "sin similitud humana detectable bajo los parametros utilizados". No debe interpretarse como ausencia absoluta de homologia.

## Prioridad de resolucion

La capa sigue pasando por el resolvedor:

1. `data_user/human_homologs.csv`.
2. datos curados o locales ya materializados.
3. ortologia local reproducible si existe.
4. TSV DIAMOND cacheado o ejecucion DIAMOND si esta permitida.
5. UniProt por nombre como evidencia auxiliar no concluyente.
6. estado no resuelto.

## Instalacion de DIAMOND en Ubuntu/WSL

Ejemplo:

```bash
sudo apt update
sudo apt install diamond-aligner
diamond --version
```

Tambien puede instalarse desde binarios oficiales de DIAMOND si se necesita una version especifica. Registrar la version en los resultados es parte de la auditoria.

## Preparar el proteoma humano

La referencia recomendada es el proteoma humano de UniProt `UP000005640`, pero debe suministrarse de forma explicita. El repositorio no incluye ni simula un proteoma humano completo en rutas de ejecucion.

La configuracion permite ajustar `reference_fasta_path`, `database_prefix`, `reference_proteome_accession` y `allow_download`. El proveedor DIAMOND esta desactivado por defecto, sus rutas de referencia estan vacias y tanto `allow_download` como `allow_execution` son `false`. Por ello una ejecucion normal no consulta la red, no crea una base y no invoca el binario DIAMOND.

Los unicos datos DIAMOND incluidos en el repositorio son fixtures sinteticos pequenos ubicados en `tests/fixtures/human_homology_synthetic/`. Se usan exclusivamente en pruebas automatizadas: no representan el proteoma humano real y no constituyen evidencia cientifica.

## Materializacion del FASTA candidato en validaciones online

La descarga de secuencias candidatas se controla con `online_source_mode`, de forma separada a `execution_mode` de DIAMOND. `online_optional`, `cache_first` y `auto` permiten consultar UniProt solamente para accesiones que no tengan una secuencia reutilizable. `offline_only`, `local` y `api_stub` nunca abren red. El orden es: FASTA existente, secuencias incluidas en la semilla UniProt y, finalmente, descarga acotada por `sequence_batch_size`.

El manifiesto `human_homology_candidate_fasta_manifest.json` registra `download_allowed`, `download_attempted`, `download_successful`, `retrieved_sequence_count`, `seed_sequence_count`, secuencias faltantes y el modo online efectivo. El manifiesto de DIAMOND distingue `execution_started`, `execution_completed`, `execution_failed` y un `execution_status` explícito; la falta del ejecutable, la base o sus insumos no se presenta como ejecución completada.

La configuracion aislada de `run_online_only_validation.py` se genera actualizando el mapa YAML existente. No se agregan bloques raiz `online_sources` duplicados, porque eso descartaria la configuracion completa del proveedor y restauraria accidentalmente los valores seguros `execution_mode=cache_only` y `allow_execution=false`. La configuracion del materializador FASTA nunca sustituye la configuracion de ejecucion de DIAMOND.

Los fallbacks de capas obligatorias se aplican por capa. Si `human_homology_diamond_manifest.json` registra una ejecucion o cache DIAMOND exitosa y `data_external/human_homologs.csv` contiene evidencia DIAMOND utilizable, el fallback global preserva el archivo y lo registra en `preserved_valid_layers`. Un fallo recuperable de otra fuente no puede sustituir homologia valida por `provider_not_found`.

## Escala de coberturas

DIAMOND entrega identidad (`pident`) en porcentaje de 0 a 100, pero las coberturas del contrato NODOS son proporciones de 0 a 1. La cobertura se calcula con el tramo alineado definido por `qstart/qend` y `sstart/send`, dividido entre `qlen` o `slen`; no se usa `alignment length`, porque incluye gaps y puede producir razones mayores que uno. `percent_identity` y `orthology_percent_identity` permanecen en escala 0–100.

Al reutilizar datos, las cuatro columnas de cobertura se normalizan de forma idempotente: valores de 0 a 1 se conservan, valores mayores que 1 y hasta 100 se dividen entre 100, y valores negativos o mayores que 100 pasan a NA con una bandera `invalid_<columna>` en `homology_missing_flags`. Esto evita conversiones dobles en cache.

## Reutilizar cache

Si ya existe un TSV DIAMOND validado, configurar:

```yaml
online_sources:
  human_homology_diamond:
    enabled: true
    candidate_fasta_path: data_external/candidate_proteins.faa
    cached_tsv_path: data_external/human_homology_diamond.tsv
    execution_mode: cache_only
    allow_execution: false
    reuse_cache: true
```

Con esa configuracion no se reconstruye la base ni se ejecuta DIAMOND.

## Ejecutar la capa

DIAMOND solo se ejecuta tras una activacion explicita con recursos reales o controlados:

```yaml
online_sources:
  human_homology_diamond:
    enabled: true
    execution_mode: execute
    allow_execution: true
    allow_download: false
    reference_fasta_path: /ruta/al/proteoma_humano_UP000005640.faa
    database_prefix: data_external/human_reference_UP000005640
```

`candidate_fasta_path` puede indicarse de forma explicita o materializarse en el workspace por el flujo online. Si DIAMOND falla o faltan recursos, se escriben filas no resueltas cuando hay candidatos disponibles; no se inventan valores 0 o 1.

## Auditar resultados

Revisar:

- `data_external/human_homologs.csv`
- `data_processed/normalized_human_homologs.csv`
- `data_processed/integrated_nodes.csv`
- `results/human_homologs_audit.csv`
- `results/ranking_nodos_by_gene.csv`

Las columnas de auditoria incluyen tier, estrategia, identidad, coberturas, e-value, bitscore, herramienta, version y referencia.

## Limitaciones actuales

- DIAMOND detecta similitud de secuencia, no prueba funcion ni riesgo toxicológico por si solo.
- Similitud parcial puede reflejar dominios conservados y debe revisarse en contexto.
- Un no hit depende del proteoma, sensibilidad, umbral y version de base usados.
- La capa no reemplaza curacion experta ni evidencia experimental.

## Pasos futuros sugeridos

- Agregar busqueda reciproca o criterios de ortologia mas estrictos para separar homologia, paralogia y similitud de dominio.
- Incorporar anotacion de dominios conservados para explicar hits parciales.
- Versionar manifiestos de ejecucion DIAMOND por organismo.
- Conectar proteomas candidatos por organismo sin saltar el resolvedor de capas.
