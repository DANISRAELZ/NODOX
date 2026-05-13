# Scoring

El scoring es la traduccion cuantitativa de la Teoria de Nodos Funcionales:
convierte capas de evidencia, procedencia y confianza en prioridades
terapeuticas explicables. Ningun organismo demo, snapshot o conector define por
si mismo el ranking.

## Baseline legacy

Se conserva el score histórico para comparación:

```text
legacy_score_final =
  essentiality * w1
  + virulence_support * w2
  + no_human_homolog * w3
  + physical_accessibility * w4
  - legacy_host_risk * w5
```

## Scores Fase 2

### `antibiotic_target_score`

Favorece:

- esencialidad
- seguridad para el hospedero
- conservación
- factibilidad de pequeña molécula
- baja redundancia
- confianza de evidencia

### `antivirulence_target_score`

Favorece:

- virulencia
- accesibilidad física
- factibilidad para anticuerpo
- reducción de daño al hospedero
- seguridad para el hospedero
- confianza de evidencia

### `functional_node_score`

Favorece:

- centralidad de red
- cuellos de botella
- dependencia funcional
- baja redundancia
- confianza de evidencia

### `meta_priority_score`

Integra los tres scores anteriores usando pesos configurables en `config/params.yaml`.

### `therapeutic_priority_score`

Integra `meta_priority_score`, seguridad frente al hospedero, dano potencial al
hospedero, acceso al sitio de infeccion y contexto durante infeccion. La salida
principal conserva el score total y tambien exporta la descomposicion por
variable:

- `therapeutic_priority_meta_priority_score_contribution`
- `therapeutic_priority_host_safety_score_contribution`
- `therapeutic_priority_host_damage_score_contribution`
- `therapeutic_priority_infection_site_access_score_contribution`
- `therapeutic_priority_infection_context_score_contribution`
- `therapeutic_priority_contribution_summary`

La suma de las contribuciones debe coincidir con `therapeutic_priority_score`,
salvo redondeos de CSV. Estas columnas son explicativas: no cambian la formula.

### `evolutionary_escape_risk_score`

La subcapa `evolutionary_escape_risk` estima riesgo de escape evolutivo sin
reemplazar los scores existentes. Aumenta con tolerancia mutacional, redundancia,
rutas compensatorias y riesgo de emergencia de resistencia. Disminuye con alto
costo fitness, restriccion evolutiva y dependencia multinodo.

El pipeline exporta una penalizacion moderada:

```text
evolutionary_adjusted_meta_priority_score =
  meta_priority_score * (1 - penalty_weight * evolutionary_escape_risk_score)
```

Por defecto `penalty_weight = 0.15` y `meta_priority_score` se conserva para no
romper compatibilidad. La columna ajustada permite revisar el efecto evolutivo
sin ocultar el ranking original.

## Modos de ejecución

- `legacy`: exporta como ranking principal el score Fase 1.
- `phase2`: exporta como ranking principal el ranking basado en `meta_priority_score`.
- `compare`: mantiene Fase 2 como salida principal y añade comparación explícita con legacy.

## Explicabilidad

Cada candidato incluye:

- `top_positive_drivers`
- `top_negative_drivers`
- `confidence_summary`
- `missing_evidence_flags`
- `host_risk_audit_summary`
- `therapeutic_priority_contribution_summary`
- `provenance_status`
- `retrieval_mode`
- `cache_status`

`top_negative_drivers` ahora representa las mayores carencias relativas frente al score ideal,
no solo pesos negativos explícitos.

`host_risk_audit_summary` no cambia el score. Resume la procedencia de la
seguridad frente al hospedero: proveedor usado, estado de recuperacion, regla,
solapamiento de dominios, penalizacion de criticidad humana, essentialidad
humana auxiliar y faltantes marcados.

## Sensibilidad

Se calculan escenarios alternativos de pesos meta:

- `baseline_like`
- `antivirulence_focus`
- `network_focus`

La salida `results/sensitivity_analysis.csv` muestra score, rank y delta de rango
respecto al ranking base.

## Proxies endurecidas con datos disponibles

Las siguientes variables ya no usan defaults neutros:

- `domain_overlap_score`: derivada de `human_homolog` y `evalue`
- `infection_site_access`: derivada de `localization`
- `host_damage_reduction_potential`: proxy derivada de virulencia y accesibilidad
- `disease_severity_association`: proxy derivada de señal de virulencia
- `clinical_impact_score`: combinación proxy de severidad, reducción potencial de daño y acceso

## Expansión terapéutica fase 1

La primera expansión científica añade una capa terapéutica explícita sin
romper los scores existentes.

Nuevas variables:

- `host_damage_score`
- `infection_site_access_score`
- `infection_context_score`
- `therapeutic_role`
- `therapeutic_priority_score`

Capas empíricas opcionales ya soportadas:

- `clinical_impact.csv`
- `curated_disease_context.csv`
- `therapy_site_context.csv`

Si están presentes, el pipeline prefiere esos valores frente a la proxy derivada
y actualiza las banderas `*_is_proxy`.

Reglas generales:

- alta esencialidad + buena accesibilidad + bajo riesgo al hospedero favorece `bactericidal_candidate`
- alta virulencia + bajo riesgo al hospedero + acceso aceptable favorece `antivirulence_candidate`
- señal funcional alta sin letalidad fuerte favorece `sensitizer_candidate`
- soporte fuerte para varias estrategias favorece `mixed_strategy_candidate`
- evidencia insuficiente o riesgo alto favorece `low_priority_candidate`

La sensibilidad ahora también cubre `therapeutic_priority` y reporta si el
`therapeutic_role` cambia respecto al baseline.

Estas variables deben interpretarse como aproximaciones transparentes, no como mediciones biológicas definitivas.
