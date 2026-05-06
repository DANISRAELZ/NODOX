# Scoring Conceptual de Fase 3

## Proposito

Este documento describe una propuesta conceptual para una Fase 3 llamada Teoria de Nodos Funcionales y Robustez Evolutiva. No implementa cambios. Sirve como especificacion inicial para discutir columnas, pesos, confianza y relacion con Fase 2.

## Relacion entre Fase 2 y Fase 3

Fase 2 ya produce:

- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `therapeutic_priority_score`
- `therapeutic_role`
- auditorias de procedencia, sensibilidad y contexto terapeutico

Fase 3 no deberia reemplazar esos resultados. Deberia agregar una lectura opcional enfocada en robustez evolutiva:

- que tan dificil es escapar;
- que costo tiene escapar;
- cuantas rutas compensatorias existen;
- si el escape crea sensibilidad colateral;
- si el nodo es esencial en el nicho de infeccion.

## Campos nuevos conceptuales

Campos candidatos para una implementacion futura:

- `functional_node_theory_score`
- `contextual_essentiality_score`
- `mutational_tolerance_score`
- `fitness_cost_score`
- `compensation_difficulty_score`
- `evolutionary_escape_risk_score`
- `evolutionary_space_constraint_score`
- `collateral_sensitivity_potential`
- `paralog_compensation_score`
- `metabolic_bypass_score`
- `phase3_evidence_confidence_score`
- `phase3_missing_evidence_flags`
- `meta_priority_score_v3`
- `direct_host_damage_score`
- `colonization_score`
- `immune_evasion_score`
- `biofilm_persistence_score`
- `toxin_activity_score`
- `nutritional_immunity_escape_score`
- `quorum_sensing_score`
- `virulence_severity_score`

Cada campo debe tener:

- rango definido, idealmente 0 a 1;
- interpretacion biologica clara;
- fuente o proxy explicito;
- bandera de faltante o proxy;
- contribucion descomponible al score final.

## Formula real de functional_node_theory_score

La implementacion inicial vive en `src/nodos_funcionales/functional_node_theory.py`.
Es independiente y no cambia el ranking principal de Fase 2.

```text
functional_node_theory_score =
  w_functional_node * functional_node_score
  + w_contextual_essentiality * contextual_essentiality_score
  + w_pleiotropy * pleiotropy_score
  + w_conservation * conservation_score
  + w_evolutionary_constraint * evolutionary_space_constraint_score
  + w_evidence_quality * evidence_quality_score
  - p_redundancy * redundancy_penalty
  - p_escape * evolutionary_escape_risk_score
  - p_biofilm * biofilm_escape_penalty
  - p_hgt * horizontal_transfer_penalty
  - p_host_similarity * host_similarity_penalty
```

Interpretacion:

- sube si el nodo es funcionalmente importante, contextual, costoso de evadir y dificil de compensar;
- baja si tiene redundancia funcional, riesgo de escape, penalizacion por biofilm, transferencia horizontal o similitud con hospedero;
- se normaliza al rango 0-1;
- agrega `functional_node_theory_label` y `functional_node_theory_confidence`;
- reporta penalizaciones, faltantes y limites de confianza en `audit_flags`.

`confidence_ceiling` no reduce necesariamente el score biologico. Limita la confianza reportada:

```text
functional_node_theory_confidence =
  min(evidence_quality_score, confidence_ceiling)
```

Etiquetas cualitativas:

- `high_confidence_functional_node`
- `promising_but_evolutionary_risk`
- `central_but_redundant`
- `antivirulence_candidate`
- `weak_candidate`
- `insufficient_evidence`

## Formula conceptual de meta_priority_score_v3

Formula conceptual, no implementada:

```text
meta_priority_score_v3 =
  a1 * meta_priority_score
  + a2 * therapeutic_priority_score
  + a3 * functional_node_theory_score
  + a4 * host_safety_score
  + a5 * phase3_evidence_confidence_score
  - a6 * evolutionary_escape_risk_score
```

Esta formula mantendria continuidad con Fase 2, pero agregaria robustez evolutiva. No debe activarse como ranking principal hasta tener validacion y sensibilidad.

## Reglas para confianza y evidencia

Fase 3 deberia ser estricta con procedencia:

- evidencia experimental directa: mayor confianza;
- literatura curada: confianza media-alta;
- bases externas estables: confianza media;
- proveedor controlado: confianza moderada;
- proxy derivada: confianza baja;
- faltante: valor neutral o penalizacion explicita, segun variable.

Reglas minimas:

- No inventar evidencia evolutiva.
- No convertir ausencia de datos en bajo riesgo.
- Reportar `phase3_missing_evidence_flags`.
- Mantener `source_name`, `source_type`, `retrieval_status`, `confidence` y banderas de usuario/cache/external/proxy.
- Separar score biologico de score de confianza.

La implementacion inicial de este control vive en `src/nodos_funcionales/evidence_quality.py`. No elimina la confianza previa de Fase 2; agrega una capa de auditoria con:

- `evidence_source_type`
- `user_data_support`
- `curated_literature_support`
- `external_database_support`
- `experimental_support`
- `demo_data_penalty`
- `controlled_provider_cap`
- `evidence_quality_score`
- `confidence_ceiling`
- `evidence_notes`

### Techos de confianza

`confidence_ceiling` limita la confianza maxima segun procedencia:

```text
demo only -> max 0.40
controlled provider only -> max 0.50
external database -> max 0.70
curated literature -> max 0.80
user data + external + curated -> max 0.95
experimental validation -> max 1.00
```

Si el score bruto de evidencia supera el techo permitido, se recorta y se agrega `confidence_capped` en `audit_flags`. Los proveedores controlados pueden orientar hipotesis, pero no elevan por si solos la confianza fuerte.

## Interpretacion de variables clave

### contextual_essentiality_score

Mide si el nodo importa en el nicho real de infeccion, no solo en laboratorio.

### evolutionary_space_constraint_score

Mide si intervenir el nodo reduce rutas viables de escape.

### evolutionary_escape_risk_score

Mide riesgo de que el patogeno encuentre resistencia viable con costo aceptable.

### collateral_sensitivity_potential

Mide si escapar del nodo puede crear vulnerabilidad frente a otro tratamiento.

### compensation_difficulty_score

Mide que tan dificil es compensar la perturbacion por redundancia, bypass o regulacion alternativa.

### virulence_severity_score

Mide severidad antivirulencia integrada a partir de subcapas biologicamente separadas. La implementacion inicial esta en `src/nodos_funcionales/virulence_layers.py` y no reemplaza `antivirulence_target_score`.

Subcapas:

- `direct_host_damage_score`: toxinas, proteasas, hemolisinas o enzimas de dano tisular.
- `colonization_score`: adhesinas, pili, fimbriae, proteinas de superficie o colonizacion temprana.
- `immune_evasion_score`: capsula, resistencia a complemento, evasion de fagocitosis o antigenicidad.
- `biofilm_persistence_score`: matriz, alginato, biofilm, persistencia o adhesion sostenida.
- `toxin_activity_score`: toxinas y sistemas de secrecion con dano directo.
- `nutritional_immunity_escape_score`: sideroforos, captacion de hierro, hemo o escape a inmunidad nutricional.
- `quorum_sensing_score`: reguladores o senales tipo quorum sensing, por ejemplo `las`, `rhl`, `pqs`, `lux` o `agr`.

Formula conceptual actual:

```text
virulence_severity_score =
  direct_host_damage_score * direct_host_damage_weight
  + colonization_score * colonization_weight
  + immune_evasion_score * immune_evasion_weight
  + biofilm_persistence_score * biofilm_persistence_weight
  + toxin_activity_score * toxin_activity_weight
  + nutritional_immunity_escape_score * nutritional_immunity_escape_weight
  + quorum_sensing_score * quorum_sensing_weight
```

La salida agrega auditoria en `audit_flags` para indicar si las subcapas fueron explicitas o inferidas. En esta etapa, `antivirulence_target_score` se conserva para compatibilidad con Fase 2.

## Salidas esperadas futuras

Una implementacion futura podria producir:

- `data_processed/phase3_features.csv`
- `data_processed/scored_nodes_phase3.csv`
- `results/ranking_nodos_phase3.csv`
- `results/phase3_score_decomposition.csv`
- `results/evolutionary_escape_audit.csv`
- `results/collateral_sensitivity_audit.csv`

Estas salidas deberian ser opcionales y no reemplazar `ranking_nodos.csv` hasta que el usuario lo configure explicitamente.

## Limitaciones actuales

- No existe todavia evidencia suficiente para calcular todos los campos.
- No hay formula calibrada experimentalmente.
- La propuesta requiere tests de sensibilidad para evitar sobreinterpretacion.
- El scoring Fase 3 debe ser desactivado por defecto en una primera implementacion.

## Paso futuro sugerido

Antes de implementar scores, crear plantillas de datos opcionales para evidencia evolutiva y sensibilidad colateral, junto con auditorias que muestren cobertura y faltantes.
## Clasificacion gradual actualizada

Fase 3 ya no interpreta toda confianza baja como `insufficient_evidence`.
Ahora separa:

- `insufficient_evidence`: no hay evidencia real suficiente.
- `exploratory_candidate`: existen senales parciales, pero la confianza sigue baja.
- `weakly_supported_candidate`: hay evidencia util, aunque incompleta.
- `moderately_supported_candidate`: varias capas reales convergen.
- `strongly_supported_candidate`: score funcional fuerte y evidencia real convergente.
- `deprioritized_due_to_negative_evidence`: evidencia real sugiere riesgo, por
  ejemplo similitud con hospedero o escape evolutivo alto.

## Evidence Quality y Confidence Ceiling

`evidence_quality_score` resume la calidad de la evidencia disponible por
candidato. `confidence_ceiling` limita la confianza maxima permitida por la
procedencia de los datos.

Categorias usadas:

- `user_curated`
- `literature_curated`
- `external_real`
- `computed_from_real_data`
- `controlled_provider`
- `proxy_inference`
- `default_value`
- `demo_data`
- `missing`

Los datos demo, defaults y proxies no elevan la confianza final como si fueran
evidencia real. La ausencia de datos reduce confianza, pero no cuenta como
evidencia negativa. La evidencia negativa real se reporta y penaliza de forma
separada.
