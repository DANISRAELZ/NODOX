# Functional Node Theory Activation

## Proposito cientifico

Esta fase activa una lectura explicita de Teoria de Nodos Funcionales sin reemplazar el ranking terapeutico existente. El ranking terapeutico responde si un blanco parece farmacologicamente util. El ranking funcional responde si el blanco tiene evidencia computacional de reorganizar o condicionar funciones criticas del sistema biologico del patogeno.

## Variables nuevas o formalizadas

- `functional_node_theory_score`: score conceptual de soporte como Nodo Funcional.
- `functional_node_theory_confidence`: confianza conservadora limitada por calidad de evidencia y procedencia.
- `functional_node_theory_label`: etiqueta interpretativa dependiente de score, confianza y procedencia.
- `functional_node_therapeutic_exploitability_score`: estimacion conservadora de nodo funcional que ademas parece explotable terapeuticamente.
- `meets_minimum_functional_node_evidence`: regla booleana de evidencia minima.
- `functional_impact_component`: senal de impacto funcional o red.
- `dependency_component`: senal de dependencia biologica, virulencia, esencialidad o impacto clinico.
- `redundancy_constraint_component`: baja sustituibilidad, conservacion o restriccion evolutiva.
- `context_component`: relevancia en contexto de infeccion o accesibilidad.
- `host_safety_component`: seguridad relativa frente al hospedero.
- `evidence_quality_component`: calidad/cobertura de evidencia disponible.

## Reglas de scoring

El score teorico combina senales positivas ya existentes (`functional_node_score`, esencialidad contextual, pleiotropia, conservacion, restriccion evolutiva y calidad de evidencia) y resta penalizaciones de redundancia, escape evolutivo, biofilm, transferencia horizontal y similitud al hospedero.

La etiqueta no depende solo del score. Un candidato con score alto pero evidencia `unresolved`, `demo_only`, `placeholder`, `provider_not_implemented`, `provider_not_found`, `missing_optional_layer` o `controlled_context` no puede clasificarse como `high_confidence_functional_node`.

Etiquetas usadas:

- `high_confidence_functional_node`
- `moderate_confidence_functional_node`
- `low_confidence_functional_node_candidate`
- `hypothesis_only_insufficient_evidence`
- `not_supported_as_functional_node`
- `unresolved_evidence_candidate`

## Outputs nuevos

- `results/ranking_functional_nodes.csv`
- `results/ranking_functional_nodes_by_gene.csv`
- `results/functional_node_theory_audit.csv`
- `results/functional_node_theory_audit.md`
- `results/theory_of_nodes_report.md`

Estos archivos no reemplazan ni cambian el significado de `ranking_nodos.csv`, `ranking_nodos_legacy.csv`, `ranking_snapshot.csv`, `meta_priority_score` ni `therapeutic_priority_score`.

## Universo evaluado

La exportacion de Teoria de Nodos Funcionales usa el universo mas completo disponible entre el ranking terapeutico, `data_processed/scored_nodes.csv`, `data_processed/phase2_features.csv` y un `results/ranking_nodos.csv` preexistente. `data_processed/phase3_features.csv` puede aportar columnas adicionales solo si no reduce el universo evaluado. Esto evita que una corrida con `phase3.enabled: false` o con placeholders de Fase 3 limite `ranking_functional_nodes.csv` y `functional_node_theory_audit.csv` a registros semilla.

## Limitaciones actuales

El ranking funcional puede contener hipotesis computacionales cuando las capas reales aun esten incompletas. La ausencia de evidencia no se interpreta como evidencia negativa, pero reduce confianza y bloquea declaraciones robustas. Los resultados no son validacion experimental ni recomendacion clinica.

## Pasos futuros sugeridos

1. Conectar nuevas fuentes externas reales de forma incremental detras del resolvedor por capa.
2. Priorizar capas con fuente natural estable para mejorar evidencia de red, dependencia biologica y restriccion evolutiva.
3. Agregar validacion biologica curada por organismo antes de declarar nodos de alta confianza en reportes publicables.
4. Comparar estabilidad de `functional_node_theory_score` entre organismos, cepas y contextos de infeccion.
