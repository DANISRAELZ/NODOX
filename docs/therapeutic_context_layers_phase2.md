# Capas terapeuticas contextuales - Fase 2 conservadora

## Proposito cientifico

Esta iteracion reduce la dependencia de proxies internos para tres capas
terapeuticas:

- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`

El cambio no intenta resolver evidencia clinica real completa. En su lugar,
agrega un proveedor controlado y reproducible llamado
`controlled_therapeutic_context_v1`. La version recomendada actualmente es
`controlled_therapeutic_context_v2`, que mantiene el mismo contrato de proveedor
pero separa mejor la logica biologica de cada capa.

Este proveedor materializa tablas CSV en `data_external/` usando senales ya
disponibles en el workspace, como virulencia, localizacion, conservacion y red
funcional. Su objetivo es ser mejor que un proxy invisible dentro del scoring,
pero menos fuerte que evidencia experimental o literatura curada.

## Estrategia de resolucion por capa

Las tres capas usan la arquitectura existente:

1. `data_user/`
2. `data_cache/`
3. `data_external/` mediante proveedor controlado
4. proxy/default explicito si no hay evidencia suficiente o el proveedor esta desactivado

No se cambia el contrato de `layer_resolver.py`.

## Proveedor controlado

Nombre:

- `controlled_therapeutic_context_v1`
- `controlled_therapeutic_context_v2`

Etiqueta escrita en columna `database`:

- `computed_controlled_therapeutic_context_v1`
- `computed_controlled_therapeutic_context_v2`

Columnas explicativas que agrega el proveedor:

- `controlled_context_rule`
- `controlled_context_inputs`
- `controlled_context_confidence_reason`
- `controlled_context_missing_flags`

Estado de recuperacion esperado cuando se materializa:

- `controlled_provider_materialized`

Confianza por defecto:

- `v1`: `0.62`
- `v2`: `0.66`

Interpretacion:

- Es una fuente computada y reproducible.
- No equivale a validacion experimental.
- Debe leerse como evidencia semicurada derivada de capas ya resueltas.

## Diferencias entre v1 y v2

`v1` fue una primera materializacion controlada. Era util para sacar estas capas
del proxy interno, pero las tres dimensiones compartian demasiada logica:
virulencia, acceso y contexto se influian entre si de forma fuerte.

`v2` mantiene reproducibilidad, pero separa mejor cada pregunta:

- `clinical_impact`: se enfoca en dano potencial al hospedero, virulencia y esencialidad.
- `therapy_site_context`: se enfoca en accesibilidad fisica, factibilidad molecular y barreras por localizacion.
- `curated_disease_context`: se enfoca en relevancia durante infeccion usando red funcional, conservacion, virulencia y esencialidad.

La seleccion de version es configurable por capa:

```yaml
layer_resolution:
  layers:
    clinical_impact:
      external_provider: controlled_therapeutic_context_v2
    curated_disease_context:
      external_provider: controlled_therapeutic_context_v2
    therapy_site_context:
      external_provider: controlled_therapeutic_context_v2
```

## Variables generadas

### `clinical_impact.csv`

Columnas:

- `protein_id`
- `gene`
- `host_damage_reduction_potential`
- `disease_severity_association`
- `clinical_impact_score`
- `host_damage_score`
- `database`

Reglas transparentes:

- `host_damage_reduction_potential` combina virulencia, bandera de factor de virulencia y accesibilidad por localizacion.
- `disease_severity_association` combina virulencia y bandera de factor de virulencia.
- `clinical_impact_score` combina severidad, reduccion potencial de dano y acceso.
- `host_damage_score` combina reduccion potencial de dano, severidad y virulencia.

Regla v2:

- `host_damage_score` combina principalmente `virulence_score`, `virulence_factor` y `essentiality`.
- `clinical_impact_score` resume severidad, dano al hospedero y esencialidad.
- No usa accesibilidad del sitio como eje principal, para no mezclar impacto clinico con acceso terapeutico.

Metadatos:

- `controlled_context_rule`: `clinical_impact_weighted_virulence_access_v1`
- En v2: `clinical_impact_host_damage_virulence_v2`
- `controlled_context_inputs`: valores numericos usados, por ejemplo `virulence_score`, `virulence_factor` y `localization_access`
- `controlled_context_confidence_reason`: explica que la confianza es intermedia porque la capa es computada y semicurada, no experimental
- `controlled_context_missing_flags`: lista valores reemplazados por defaults, o `none`

### `therapy_site_context.csv`

Columnas:

- `protein_id`
- `gene`
- `infection_site_access`
- `infection_site` opcional
- `access_evidence_type` opcional
- `access_evidence_reference` opcional
- `access_evidence_note` opcional
- `database`

Regla transparente:

- `infection_site_access` combina principalmente accesibilidad esperada por localizacion subcelular y una pequena modulacion por virulencia.

Regla v2:

- `infection_site_access` combina `infection_site_access`, `physical_accessibility`, `small_molecule_feasibility`, `antibody_feasibility` y una penalizacion invertida de cruce de membrana.
- No usa virulencia como componente directo, para que esta capa represente acceso terapeutico y no severidad.

Metadatos:

- `controlled_context_rule`: `therapy_site_access_localization_weighted_v1`
- En v2: `therapy_site_access_localization_barrier_v2`
- `controlled_context_inputs`: valores usados, principalmente `localization_access` y `virulence_score`
- `controlled_context_confidence_reason`: razon de confianza controlada
- `controlled_context_missing_flags`: defaults usados, o `none`

### `curated_disease_context.csv`

Columnas:

- `protein_id`
- `gene`
- `infection_context_score`
- `database`

Regla transparente:

- `infection_context_score` combina `host_damage_score`, `infection_site_access`, impacto funcional de red y conservacion.

Regla v2:

- `infection_context_score` combina impacto funcional, conservacion, virulencia y esencialidad.
- No depende directamente de `host_damage_score` ni de `infection_site_access`, para evitar que las tres capas colapsen en la misma senal.

Metadatos:

- `controlled_context_rule`: `disease_context_damage_access_function_conservation_v1`
- En v2: `disease_context_function_conservation_infection_v2`
- `controlled_context_inputs`: `host_damage_score`, `infection_site_access`, `functional_impact` y `conservation`
- `controlled_context_confidence_reason`: razon de confianza controlada
- `controlled_context_missing_flags`: defaults usados en red, conservacion o capas intermedias, o `none`

## Como leer los metadatos

Ejemplo:

```csv
protein_id,controlled_context_rule,controlled_context_inputs,controlled_context_missing_flags
PA0008,clinical_impact_weighted_virulence_access_v1,"virulence_score=0.9500; virulence_factor=1.0000; localization_access=0.9500",none
```

Lectura simple:

- la regla dice que se uso la formula de impacto clinico controlado
- los inputs muestran los valores concretos usados
- `none` indica que no se usaron defaults para esa fila

Si aparece algo como:

```text
default_network_network_centrality
```

significa que esa senal no estaba disponible y se uso el valor neutral definido
por configuracion. Esto no invalida la fila, pero reduce la fuerza
interpretativa de esa evidencia.

## Auditoria de separacion semantica

Esta iteracion agrega una salida de auditoria para verificar que las tres capas
controladas no colapsen en una misma senal numerica:

- `results/therapeutic_context_separation_audit.csv`
- `results/therapeutic_context_separation_audit.md`

La auditoria compara por pares:

- `clinical_impact` usando `host_damage_score`
- `curated_disease_context` usando `infection_context_score`
- `therapy_site_context` usando `infection_site_access`

Columnas principales:

- `score_correlation`: correlacion entre los scores de dos capas para los
  mismos candidatos.
- `input_key_overlap`: proporcion de nombres de inputs compartidos entre las
  reglas controladas.
- `left_rule` y `right_rule`: reglas dominantes que generaron cada capa.
- `separation_status`: lectura conservadora del grado de separacion.

Valores de `separation_status`:

- `separated_for_current_rules`: las capas se ven suficientemente separadas
  para las reglas actuales.
- `moderate_overlap_monitor`: hay solapamiento o correlacion moderada; conviene
  vigilar estabilidad en futuras corridas.
- `high_overlap_review_needed`: las capas podrian estar midiendo algo demasiado
  parecido y requieren revision cientifica antes de elevar confianza.

Esta auditoria no modifica scores, ranking ni clasificacion terapeutica. Su
funcion es documentar la calidad semantica de las capas controladas.

## Preparacion para reemplazar capas controladas

La salida:

- `results/controlled_replacement_readiness.csv`
- `results/controlled_replacement_readiness.md`

resume que capas siguen dependiendo de proveedor controlado, proxy o evidencia
insuficientemente trazable.

La primera ruta recomendada de reemplazo incremental es
`therapy_site_context`, porque puede cargarse como CSV curado por usuario sin
dependencias nuevas:

```text
data_user/therapy_site_context.csv
```

Columnas recomendadas:

```text
protein_id
gene
infection_site_access
infection_site
access_evidence_type
access_evidence_reference
access_evidence_note
database
```

Cuando esta tabla se coloca en `data_user/`, la estrategia `user_preferred`
mantiene la prioridad del usuario y evita consultar innecesariamente el
proveedor controlado para esa capa.

La evidencia de sitio tambien se propaga a:

- `data_processed/scored_nodes.csv`
- `results/candidate_audit.csv`

mediante `therapy_site_context_audit_summary`, para que cada candidato conserve
sitio, tipo de evidencia, referencia, fuente y estado de recuperacion.

Para facilitar la curacion sin inventar datos, el pipeline tambien exporta:

- `results/therapy_site_context_curation_queue.csv`
- `results/therapy_site_context_curation_queue.md`

Esta cola toma los candidatos priorizados y deja campos vacios para completar:

```text
curated_infection_site_access
curated_infection_site
curated_access_evidence_type
curated_access_evidence_reference
curated_access_evidence_note
curated_database
```

La cola no se usa como input automaticamente. Sirve como hoja de trabajo para
preparar un futuro `data_user/therapy_site_context.csv` con evidencia real y
trazable.

## Ejemplos de uso

### Usar datos del usuario

Colocar archivos en `data_user/` con los nombres esperados:

```text
data_user/clinical_impact.csv
data_user/curated_disease_context.csv
data_user/therapy_site_context.csv
```

Ejemplo minimo para `clinical_impact.csv`:

```csv
protein_id,gene,host_damage_reduction_potential,disease_severity_association,clinical_impact_score,host_damage_score,database
PA0008,lasB,0.91,0.92,0.93,0.94,curated_user_clinical_review
```

Ejemplo minimo para `curated_disease_context.csv`:

```csv
protein_id,gene,infection_context_score,database
PA0008,lasB,0.89,curated_user_disease_context
```

Ejemplo minimo para `therapy_site_context.csv`:

```csv
protein_id,gene,infection_site_access,infection_site,access_evidence_type,access_evidence_reference,access_evidence_note,database
PA0008,lasB,0.88,lung_abscess,curated_literature,doi_or_local_reference,short_note,curated_user_site_context
```

Las columnas de evidencia son opcionales para mantener compatibilidad, pero se
recomiendan cuando se quiera reemplazar el proveedor controlado por evidencia
mas real. `access_evidence_reference` puede ser un DOI, URL, codigo interno de
curacion o referencia local auditable.

### Usar cache local

Colocar los mismos archivos en `data_cache/`. Si no hay datos de usuario ni
datos raw ya resueltos, el cache se usa antes de consultar el proveedor
controlado.

### Usar proveedor controlado

Con la configuracion por defecto, si no existen datos de usuario, cache ni raw
para estas capas, el resolvedor llama a `controlled_therapeutic_context_v1`.

Esto materializa archivos como:

```text
data_external/clinical_impact.csv
data_external/curated_disease_context.csv
data_external/therapy_site_context.csv
```

Luego se copian a `data_raw/` y `data_cache/` si `write_cache_from_external`
esta activo.

### Forzar fallback a proxy

Para comparar contra la fase anterior, desactivar el proveedor:

```yaml
online_sources:
  therapeutic_context:
    enabled: false
```

Cuando el proveedor esta desactivado y no hay usuario/cache/raw, el resolvedor
registra la capa como proxy con:

- `source_type=proxy`
- `retrieval_status=proxy_default`
- `is_proxy=true`

## Procedencia

Las columnas de procedencia se propagan en `integrated_nodes.csv`,
`phase2_features.csv` y reportes:

- `<layer>_source_type`
- `<layer>_source_name`
- `<layer>_is_user_supplied`
- `<layer>_is_external`
- `<layer>_is_cached`
- `<layer>_is_proxy`
- `<layer>_confidence`
- `<layer>_retrieval_status`

## Limitaciones actuales

- El proveedor controlado no consulta literatura clinica ni bases externas reales.
- Las reglas son heuristicas interpretables, no evidencia experimental.
- La confianza es deliberadamente intermedia.
- Si las capas base del workspace son demo o incompletas, estas capas tambien heredan esa limitacion.
- Una correlacion baja no demuestra independencia biologica real; solo indica
  que las formulas y datos actuales no colapsan numericamente.
- Una correlacion alta no invalida automaticamente una capa; marca necesidad de
  revisar pesos, inputs o evidencia externa.

## Pasos futuros sugeridos

1. Permitir catalogos curados por organismo para `clinical_impact`.
2. Incorporar contexto de sitio de infeccion por enfermedad cuando exista evidencia curada.
3. Separar evidencia de dano directo al hospedero de severidad asociada a virulencia.
4. Comparar estabilidad del `therapeutic_role` con y sin proveedor controlado.
5. Elevar la confianza solo cuando una capa provenga de datos de usuario, literatura curada o fuente externa real estable.
