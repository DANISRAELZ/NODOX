# Scoring Theory Alignment

## Scores teoricos principales

| Score | Interpretacion teorica | Implementacion |
|---|---|---|
| `functional_node_score` | Mide si el candidato se comporta como nodo funcional en una red biologica. | Red funcional, bottleneck, dependencia y redundancia. |
| `antibiotic_target_score` | Mide potencial como blanco antimicrobiano directo. | Esencialidad, conservacion, factibilidad, selectividad y evidencia. |
| `antivirulence_target_score` | Mide potencial para reducir virulencia, dano, persistencia o adaptacion. | Virulencia, accesibilidad, dano al hospedero, seguridad y evidencia. |
| `selectivity_score` | Mide bajo riesgo relativo para el hospedero. | Alias auditable de `host_safety_score`. |
| `evolutionary_robustness_score` | Mide menor espacio de escape evolutivo. | `1 - evolutionary_escape_risk_score`, junto con auditoria de evidencia. |
| `clinical_context_score` | Mide coherencia con sitio de infeccion, contexto clinico y dano. | Combinacion de contexto, acceso y dano al hospedero. |
| `confidence_modifier` | Modula interpretacion por calidad, cobertura y procedencia. | Evidencia, cobertura y calidad de fuente. |
| `meta_priority_score` | Integra dimensiones para priorizacion global auditable. | Score modular configurable en `config/params.yaml`. |

## Compatibilidad

Las columnas historicas se conservan. Los nuevos nombres teoricos funcionan como
alias o vistas interpretativas para evitar romper outputs existentes.
