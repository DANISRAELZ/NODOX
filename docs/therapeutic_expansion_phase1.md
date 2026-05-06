# Expansión Terapéutica Científica - Fase 1

## Propósito científico

Esta fase amplía la priorización actual para responder una pregunta más
terapéutica: no solo si un nodo bacteriano parece importante, sino también
qué tipo de intervención podría justificar y con qué contexto biológico mínimo.

La expansión sigue siendo:

- interpretable
- reproducible
- compatible con la arquitectura existente
- explícita sobre proxies y faltantes

No introduce modelos de machine learning ni reemplaza el pipeline actual.
Extiende la capa de `scoring` con variables derivadas a partir de evidencia ya
integrada.

## Nuevas variables

### `host_damage_score`

Resume el potencial de que intervenir sobre ese nodo ayude a reducir daño al
hospedero dentro del modelo actual.

Se deriva de:

- `host_damage_reduction_potential`
- `disease_severity_association`
- `virulence_support`

Interpretación:

- alto: el nodo parece más vinculado a procesos que sostienen daño durante la infección
- bajo: el nodo no muestra una señal fuerte de daño mediado por infección

### `infection_site_access_score`

Formaliza la accesibilidad terapéutica en el sitio de infección a partir de la
localización subcelular ya usada por el pipeline.

En esta fase es una proyección directa de:

- `infection_site_access`

Interpretación:

- alto: el nodo parece más accesible en contexto infeccioso
- bajo: el acceso terapéutico parece más difícil

### `infection_context_score`

Resume relevancia contextual durante la infección combinando:

- `host_damage_score`
- `infection_site_access_score`
- `functional_impact_score`
- `conservation_score`

Interpretación:

- alto: el nodo combina acceso, contexto de daño y soporte funcional/conservación
- bajo: el nodo todavía no muestra una señal contextual suficientemente fuerte

### `therapeutic_role`

Clasificación discreta y legible del tipo de uso terapéutico más plausible.

Valores posibles:

- `bactericidal_candidate`
- `antivirulence_candidate`
- `sensitizer_candidate`
- `mixed_strategy_candidate`
- `low_priority_candidate`

### `therapeutic_priority_score`

Score compuesto para priorización terapéutica temprana.

Integra:

- `meta_priority_score`
- `host_safety_score`
- `host_damage_score`
- `infection_site_access_score`
- `infection_context_score`

## Reglas de clasificación usadas

Las reglas son conservadoras y editables en `config/params.yaml`.

### `bactericidal_candidate`

Se asigna cuando hay:

- esencialidad alta
- buena accesibilidad en sitio de infección
- seguridad aceptable para el hospedero
- soporte suficiente del score antibiótico

Excepción conservadora añadida en esta iteración:

- si la señal bactericida ya es muy fuerte
- la seguridad para el hospedero sigue siendo aceptable
- la prioridad terapéutica ya es alta
- y el acceso está limitado pero no cae por debajo de un piso crítico

el candidato puede mantenerse como `bactericidal_candidate` con la regla
`strong_bactericidal_signal_with_limited_access` en vez de caer
automáticamente en `poor_infection_site_access`.

### `antivirulence_candidate`

Se asigna cuando hay:

- virulencia alta
- señal alta de daño al hospedero dentro del modelo
- accesibilidad al menos aceptable
- seguridad aceptable para el hospedero
- soporte suficiente del score antivirulencia

### `sensitizer_candidate`

Se asigna cuando hay:

- señal funcional alta
- contexto infeccioso alto
- sin una firma dominante de letalidad directa

Esto busca capturar nodos que podrían no ser bactericidas por sí solos, pero sí
debilitar adaptación, tolerancia o robustez funcional.

### `mixed_strategy_candidate`

Se asigna cuando:

- dos o más estrategias aparecen simultáneamente fuertes
- o el margen entre estrategias es pequeño y varias señales son competitivas

### `low_priority_candidate`

Se asigna cuando:

- la evidencia/confianza es insuficiente
- la cobertura es limitada
- el riesgo para el hospedero parece demasiado alto
- o el score terapéutico compuesto no supera un mínimo razonable

## Cómo se marca la incompletitud

Esta fase no inventa nuevas mediciones.

Si faltan capas empíricas, el pipeline:

- usa proxies ya existentes
- mantiene banderas `*_is_proxy`
- añade `therapeutic_context_missingness`
- conserva `missing_evidence_flags`

Esto permite distinguir entre:

- señal biológica integrada
- proxy derivada
- evidencia insuficiente

## Capas contextuales opcionales ya soportadas

Esta iteración ya puede incorporar, si existen en `data_raw/`, tres tablas
opcionales para reducir dependencia de proxies:

- `clinical_impact.csv`
- `curated_disease_context.csv`
- `therapy_site_context.csv`

Uso actual:

- `clinical_impact.csv` puede aportar `host_damage_reduction_potential`, `disease_severity_association`, `clinical_impact_score` y opcionalmente `host_damage_score`
- `curated_disease_context.csv` puede aportar `infection_context_score`
- `therapy_site_context.csv` puede aportar `infection_site_access`

Si estas tablas están presentes y válidas, el pipeline usa esos valores como
señal empírica preferente y deja de marcar las columnas correspondientes como
proxy.

## Limitaciones actuales

- `host_damage_score` sigue dependiendo de proxies de virulencia y no de medidas directas de daño tisular o inmunopatología.
- `infection_site_access_score` todavía depende de localización subcelular, no de farmacocinética ni de penetración observada en tejido.
- `infection_context_score` no incorpora todavía datos reales de nicho anatómico, etapa temporal de infección o expresión específica in vivo.
- `therapeutic_role` es una clasificación por reglas interpretables, no una validación experimental.
- `therapeutic_priority_score` sirve para ordenamiento interno reproducible, no para decisión clínica directa.

## Escalado en fases futuras

La arquitectura actual ya deja preparada una expansión ordenada:

1. incorporar capas reales para `clinical_impact.csv`, `curated_disease_context.csv` y `therapy_site_context.csv`
2. reemplazar proxies por observaciones curadas cuando existan
3. refinar `infection_context_score` con contexto por nicho y fase de infección
4. separar con más precisión nodos sensibilizadores de nodos antivirulencia
5. validar si `therapeutic_role` cambia al introducir capas no demo de red, conservación y anotación de hospedero

## Sensibilidad terapéutica

La salida `results/sensitivity_analysis.csv` ya incluye escenarios de
`therapeutic_priority` con:

- score reordenado
- cambio de rango respecto al baseline
- `therapeutic_role` por escenario
- bandera `role_changed_vs_base`

Esto permite medir si el rol terapéutico es estable o si cambia demasiado ante
distintas prioridades metodológicas.

Escenarios activos en esta iteración:

- `safety_first`
- `context_first`
- `bactericidal_first`
- `damage_control_first`

Además del resumen por rol, el pipeline exporta `therapeutic_rule_summary.csv`
para distinguir por qué regla concreta un candidato terminó clasificado,
especialmente dentro de `low_priority_candidate`.

## Archivos impactados en esta fase

- `src/nodos_funcionales/scoring.py`
- `src/nodos_funcionales/reporting.py`
- `src/nodos_funcionales/config.py`
- `config/params.yaml`
- tests y documentación asociada
