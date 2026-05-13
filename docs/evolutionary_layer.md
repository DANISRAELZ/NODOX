# Evolutionary Layer

## Proposito teorico

La robustez evolutiva es un eje central de la Teoria de Nodos Funcionales. Un
candidato no solo debe parecer importante ahora; tambien debe evaluarse por el
espacio evolutivo disponible para evadir una perturbacion terapeutica.

## Variables principales

- `evolutionary_escape_risk_score`: riesgo agregado de escape.
- `evolutionary_constraint_score`: restriccion evolutiva estimada.
- `mutation_tolerance_score`: tolerancia a variacion.
- `functional_redundancy_escape_score` / `pathway_redundancy`: redundancia o
  compensacion funcional.
- `paralog_count`: copias o paralogos potencialmente compensatorios.
- `mobile_context`: contexto movil o transferible.
- `hgt_context`: senal de transferencia horizontal.
- `recombination_context`: senal de recombinacion.
- `resistance_association`: asociacion con resistencia o supervivencia bajo
  tratamiento.
- `evolutionary_robustness_score`: lectura favorable derivada de bajo riesgo
  de escape.
- `reduced_evolutionary_space_score`: lectura favorable de menor espacio de
  escape.

## Reglas interpretativas

Aumentan `evolutionary_escape_risk_score`:

- alta tolerancia mutacional;
- alta redundancia;
- alto `paralog_count`;
- contexto movil;
- HGT;
- recombinacion;
- asociacion fuerte con resistencia.

Aumentan `evolutionary_constraint_score`:

- baja tolerancia mutacional;
- baja redundancia;
- pocos paralogos;
- ausencia demostrada con metodo de contexto movil/HGT/recombinacion;
- baja asociacion con resistencia;
- conservacion funcional relevante.

## Limite critico

Bajo riesgo evolutivo no significa ausencia de resistencia. Solo significa que,
con la evidencia disponible, el nodo parece tener menor espacio de escape que
otros candidatos comparables.
