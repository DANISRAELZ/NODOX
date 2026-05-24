# Interpretation Limits

Estas advertencias aplican a todos los rankings y reportes:

- Nodos Funcionales es una plataforma de priorizacion terapeutica basada en
  evidencia, no un predictor clinico definitivo.
- Un score alto no equivale a validacion experimental.
- Un score alto no implica que exista un farmaco disponible.
- `therapeutic_priority_score` y `evidence_confidence_score` responden preguntas
  distintas: prioridad dentro del modelo y confianza de evidencia disponible.
- Un `therapeutic_priority_score` alto no implica confianza alta.
- Un gen esencial no es automaticamente un buen blanco terapeutico.
- Un factor de virulencia no es automaticamente prioritario.
- Un hub no es automaticamente drogable.
- La ausencia de evidencia no equivale a evidencia negativa.
- Evidencia faltante, incompleta o proxy no equivale a bajo riesgo.
- La informacion online general no sustituye datos especificos del usuario.
- Bajo riesgo evolutivo no significa ausencia de resistencia.
- El ranking representa hipotesis terapeuticas priorizadas, no recomendaciones
  clinicas.
- No constituye recomendacion terapeutica ni sustituye evaluacion medica,
  microbiologica o farmacologica.
- Los scores son evidencia de soporte dentro del modelo, no confirmacion
  definitiva.
- Toda aplicacion requiere validacion experimental y clinica externa.

## Lectura recomendada

Los scores deben leerse junto con:

- procedencia;
- confianza;
- evidencia faltante;
- evidencia negativa real, si existe;
- dependencia de proxies o datos demo;
- estabilidad del rol terapeutico;
- riesgo evolutivo y restriccion del escape.

## Tabla interpretativa

| Lectura combinada | Interpretacion conservadora |
| --- | --- |
| Score alto / confianza alta | Hipotesis priorizada con mejor soporte relativo; aun requiere validacion externa. |
| Score alto / confianza baja | Hipotesis exploratoria priorizada por las reglas actuales; revisar proxies, faltantes y procedencia antes de confiar en ella. |
| Score bajo / confianza alta | La evidencia trazable sostiene baja prioridad relativa bajo el modelo actual; no equivale por si sola a irrelevancia biologica. |
| Score bajo / confianza baja | Lectura debil; no usar ausencia de prioridad como evidencia negativa. |
| Confianza no evaluada | No debe interpretarse como confianza alta ni baja; pedir procedencia y evidencia antes de concluir. |
| Alto riesgo evolutivo / baja confianza | Advertencia de escape posible con soporte insuficiente; pedir evidencia evolutiva directa o curada. |
| Bajo riesgo aparente / evidencia insuficiente | Riesgo no resuelto; faltantes y proxies no prueban durabilidad ni seguridad. |
| Riesgo evolutivo ausente o incierto | No equivale a bajo escape evolutivo; la subcapa evolutiva modula la interpretacion, pero no sustituye funcionalidad, selectividad, accesibilidad, confianza ni validacion experimental. |

## Modo conservador

El modo conservador es una regla de lectura para reportes y revision experta. No
convierte falta de datos en seguridad. Penaliza o advierte cuando la lectura
depende de evidencia proxy, alta redundancia, alto `paralog_count`,
`mobile_context`, `hgt_context`, `recombination_context`,
`resistance_association` o baja confianza.

La subcapa evolutiva modula esa lectura de robustez y escape. No debe opacar la
funcionalidad del nodo, la selectividad frente al hospedero, la accesibilidad en
el sitio de infeccion ni la evidencia trazable que sostiene el ranking.

En reportes, el modo conservador es interpretativo: no modifica
`therapeutic_priority_score`, `evidence_confidence_score`, pesos ni ranking. Sus
umbrales simples, como confianza baja menor a 0.50, prioridad alta mayor o igual
a 0.65, riesgo evolutivo alto mayor o igual a 0.65 o `paralog_count` alto mayor
o igual a 2, solo disparan advertencias. Tambien advierte sobre
`evolutionary_escape_risk` ausente o incierto, `evolutionary_constraint` bajo,
`mutation_tolerance` alta o incierta, redundancia de via, contexto movil,
transferencia horizontal, recombinacion, asociacion con resistencia y
procedencia demo/proxy/cache/controlada.

## Matriz final de interpretacion

La matriz final combina prioridad, confianza, riesgo evolutivo, procedencia y
lectura conservadora sin modificar scores ni ranking. Sus categorias son
interpretativas: `strong_candidate_for_experimental_validation`,
`prioritized_hypothesis_limited_evidence`,
`evidence_supported_but_low_priority`, `insufficient_information`,
`evolutionary_caution`, `provenance_limited_interpretation` y
`user_curated_requires_traceability`. Ninguna categoria confirma uso clinico:
toda aplicacion requiere validacion experimental.

La columna `final_interpretation_matrix` se conserva en las explicaciones de
candidatos exportables, incluyendo CSV y Markdown, y puede serializarse a JSON
desde el mismo DataFrame sin recalcular ni reordenar candidatos.

El cierre documental de estas garantias esta en
`docs/user_curated_interpretation_closure_audit.md`.
