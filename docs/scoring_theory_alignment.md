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

## Lectura prioridad/confianza

`therapeutic_priority_score` y `evidence_confidence_score` no son sustituibles.
El primero prioriza hipotesis dentro del modelo; el segundo indica soporte
trazable. Un score alto con confianza baja es una hipotesis fragil, no un
candidato confirmado. Una confianza alta con score bajo indica evidencia
disponible, pero no prioridad terapeutica alta bajo las reglas actuales. Si la
confianza no fue evaluada, no debe asumirse alta ni baja.

La evidencia insuficiente no equivale a bajo riesgo. El riesgo evolutivo
ausente o incierto tampoco equivale a bajo escape: la subcapa evolutiva modula
la interpretacion, pero no sustituye funcionalidad, selectividad, accesibilidad,
confianza ni validacion experimental.

## Modo conservador interpretativo

El modo conservador agregado a explicaciones y reportes no cambia formulas,
pesos, scores ni ordenamiento. Solo etiqueta factores de cautela cuando existen
campos disponibles: baja confianza, score alto con baja confianza, demo/proxy o
cache como soporte limitado, `controlled_reference`, riesgo evolutivo alto o no
evaluado, baja restriccion evolutiva, alta tolerancia mutacional, redundancia,
paralogos, movilidad, HGT, recombinacion o asociacion con resistencia. Estos
umbrales son de lectura y auditoria, no una recalibracion cientifica.

## Matriz final interpretativa

La matriz final agrega una categoria textual por candidato a partir de
`therapeutic_priority_score`, `evidence_confidence_score`,
`evolutionary_escape_risk`, procedencia y lectura conservadora. No recalcula
scores ni cambia el ranking. Una categoria fuerte significa candidato para
validacion experimental, no candidato clinico confirmado; una categoria limitada
por evidencia, procedencia o riesgo evolutivo indica que la hipotesis necesita
mas soporte antes de interpretarse con confianza.
