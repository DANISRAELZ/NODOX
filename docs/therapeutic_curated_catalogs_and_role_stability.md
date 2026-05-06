# Catalogos terapeuticos curados y estabilidad del rol

## Proposito cientifico

Esta iteracion separa mejor cuatro ideas que antes podian leerse como equivalentes:

- dano directo al hospedero
- severidad asociada a virulencia
- contexto de sitio de infeccion
- senales derivadas de un proveedor controlado interno

El objetivo no es afirmar evidencia nueva. El objetivo es que el pipeline pueda usar evidencia curada cuando exista, seguir funcionando cuando no exista y dejar claro de donde viene cada senal.

## Fuentes aceptadas

`clinical_impact` ahora puede resolverse desde un catalogo curado por organismo antes de usar `controlled_therapeutic_context_v2`.

Ruta esperada:

```text
data_external/curated_catalogs/clinical_impact/<clave>.csv
```

Claves soportadas:

- `taxon_<taxon_id>.csv`
- `<taxon_id>.csv`
- nombre canonico del organismo en minusculas y con guiones bajos

`therapy_site_context` ahora puede resolverse desde un catalogo curado por organismo, enfermedad o sitio antes de usar el proveedor controlado.

Ruta esperada:

```text
data_external/curated_catalogs/therapy_site_context/<clave>.csv
```

Estos catalogos no saltan la arquitectura: se materializan como fuente externa de la capa y pasan por validacion, normalizacion, integracion, scoring y reporting.

## Variables nuevas

Para `clinical_impact`:

- `host_direct_damage_score`: dano directo al hospedero, por ejemplo citotoxicidad, destruccion tisular o dano inflamatorio directo.
- `virulence_associated_severity_score`: asociacion con cuadros mas graves, progresion o peor desenlace.
- `clinical_impact_catalog_source`: archivo o catalogo curado usado.
- `clinical_impact_evidence_type`: tipo de evidencia, por ejemplo `curated_literature`.
- `clinical_impact_evidence_reference`: DOI, URL, cita local o identificador trazable.
- `clinical_impact_evidence_note`: nota breve de curacion.

Para `therapy_site_context`:

- `disease_context`: enfermedad o sindrome usado como contexto.
- `syndrome`: etiqueta clinica equivalente o mas especifica.
- `disease_site_context_source`: archivo o catalogo curado usado.

Para `curated_disease_context`:

- `disease_context`: enfermedad, sindrome o modelo de infeccion usado para interpretar la senal.
- `infection_stage`: etapa o condicion de infeccion, por ejemplo `acute_infection`, `chronic_infection`, `in_vivo_model` o `not_reported`.
- `context_evidence_type`: tipo de evidencia contextual, por ejemplo `curated_literature`, `in_vivo_expression` o `clinical_association`.
- `context_evidence_reference`: DOI, URL, cita local o identificador trazable.
- `context_evidence_note`: nota breve de curacion.

Para auditoria de confianza y estabilidad:

- `confidence_source_class`
- `confidence_evidence_tier`
- `confidence_source_quality_score`
- `therapeutic_role_with_controlled_provider`
- `therapeutic_role_without_controlled_provider`
- `therapeutic_role_stability`
- `therapeutic_role_stability_explanation`
- `therapeutic_priority_controlled_delta`
- `controlled_context_max_feature_delta`
- `host_damage_score_controlled_delta`
- `infection_site_access_score_controlled_delta`
- `infection_context_score_controlled_delta`
- `therapeutic_rule_boundary_margin`
- `therapeutic_rule_boundary_proximity`
- `clinical_impact_input_status`
- `curated_disease_context_input_status`
- `therapy_site_context_input_status`
- `therapeutic_context_input_summary`
- `controlled_dependency_flags`

## Cola de curacion de impacto clinico

Esta iteracion agrega una cola de trabajo para poblar `clinical_impact` con evidencia real o literatura curada sin inventar datos.

Archivos exportados:

```text
results/clinical_impact_curation_queue.csv
results/clinical_impact_curation_queue.md
```

La cola muestra, para los candidatos priorizados, los valores actuales y deja campos vacios para curacion manual:

- `curated_host_direct_damage_score`
- `curated_virulence_associated_severity_score`
- `curated_clinical_impact_score`
- `curated_clinical_impact_evidence_type`
- `curated_clinical_impact_evidence_reference`
- `curated_clinical_impact_evidence_note`
- `curated_database`

`needs_curated_clinical_impact` queda en `true` cuando la senal actual viene de proveedor controlado, proxy, no tiene referencia trazable o no separa claramente dano directo y severidad.

## Cola de curacion de contexto de enfermedad

Esta iteracion agrega una cola de trabajo para poblar `curated_disease_context` con evidencia sobre relevancia durante infeccion, enfermedad, sindrome o estadio.

Archivos exportados:

```text
results/disease_context_curation_queue.csv
results/disease_context_curation_queue.md
```

La cola muestra los valores actuales y deja campos vacios para curacion manual:

- `curated_infection_context_score`
- `curated_disease_context`
- `curated_infection_stage`
- `curated_context_evidence_type`
- `curated_context_evidence_reference`
- `curated_context_evidence_note`
- `curated_database`

`needs_curated_disease_context` queda en `true` cuando la senal actual viene de proveedor controlado, proxy, no tiene enfermedad/estadio trazable o carece de referencia.

## Logica de confianza

La confianza se vuelve mas estricta por procedencia:

- `user`: alta si paso validacion.
- `curated` o `literature`: media-alta.
- `experimental`: media-alta.
- `controlled`: moderada.
- `proxy`: baja.
- `unknown`: neutra.

El proveedor controlado y los proxies ya no elevan la calidad opcional por encima de su clase de procedencia. Esto mantiene la interpretacion prudente aunque el pipeline siga produciendo scores completos.

## Estabilidad del rol terapeutico

El pipeline conserva el rol normal como `therapeutic_role` y lo copia a:

```text
therapeutic_role_with_controlled_provider
```

Luego calcula un escenario conservador en el que las capas controladas vuelven a proxies internos derivados de las otras capas resueltas. Ese rol se reporta como:

```text
therapeutic_role_without_controlled_provider
```

La comparacion se exporta en:

```text
results/therapeutic_role_controlled_stability.csv
results/therapeutic_role_controlled_stability_summary.csv
results/therapeutic_role_controlled_stability.md
```

Si `therapeutic_role_stability` es `changed`, el candidato depende metodologicamente de las capas controladas y debe revisarse con mas cautela.

Si `therapeutic_role_stability` es `stable`, la interpretacion ya no debe ser automatica. La estabilidad puede significar cosas distintas:

- `stable_because_controlled_values_match_local_proxies`: el rol no cambia porque los valores controlados son muy parecidos a los proxies locales.
- `stable_because_role_rule_far_from_thresholds`: el rol no cambia porque el candidato esta lejos de los umbrales de decision.
- `stable_but_scores_sensitive_review`: el rol no cambia, pero los scores se movieron lo suficiente como para revisar la dependencia metodologica.
- `stable_with_moderate_score_shift`: el rol no cambia y hay diferencias intermedias que conviene monitorear.
- `stable_without_active_controlled_context`: el rol no cambia porque no hay una capa terapeutica controlada activa; el pipeline esta trabajando con senales locales, proxies o capas vacias.

Las columnas `*_controlled_delta` muestran la diferencia entre el valor con proveedor controlado y el valor del escenario conservador sin proveedor controlado. `controlled_context_max_feature_delta` resume el mayor cambio entre dano al hospedero, acceso al sitio y contexto de infeccion. `therapeutic_rule_boundary_margin` indica que tan cerca esta el candidato del umbral mas cercano usado por las reglas.

Las columnas `*_input_status` distinguen cuatro situaciones importantes:

- `active_input`: la capa aporto valores numericos al scoring.
- `resolved_empty_or_not_normalized`: la capa fue resuelta, pero no aporto filas normalizadas utiles.
- `proxy_default_no_input_table`: el pipeline uso el fallback proxy explicito.
- `missing_or_inactive`: no hubo capa activa disponible.

Esto evita interpretar un archivo CSV vacio o una capa ausente como evidencia terapeutica real.

## Limitaciones actuales

- Los catalogos curados son archivos locales CSV; el pipeline no descarga literatura automaticamente.
- Si no existe catalogo curado, el proveedor controlado sigue activo para mantener compatibilidad.
- El escenario sin proveedor controlado es una auditoria de sensibilidad, no una verdad biologica alternativa.
- Un rol estable puede seguir dependiendo de proxies si los proxies reproducen senales similares a las del proveedor controlado.
- Una capa resuelta pero vacia no fortalece la evidencia biologica; solo conserva compatibilidad de ejecucion.
- Los scores siguen siendo una priorizacion exploratoria y requieren validacion experimental.

## Pasos futuros sugeridos

1. Poblar catalogos reales por organismo para `clinical_impact`.
2. Poblar catalogos por enfermedad para `therapy_site_context`.
3. Usar `results/clinical_impact_curation_queue.csv` para completar dano directo y severidad con referencias trazables.
4. Usar `results/disease_context_curation_queue.csv` para completar relevancia durante infeccion con referencias trazables.
5. Anadir referencias trazables por candidato.
6. Revisar manualmente los candidatos con `therapeutic_role_stability=changed`.
7. Sustituir gradualmente capas controladas por fuentes curadas o externas estables.
