# Interpretacion Conservadora User-Curated

## Proposito cientifico

Esta fase inicia la validacion real `user_curated` con una lectura conservadora.
Nodos Funcionales se usa como plataforma de priorizacion terapeutica basada en
evidencia dentro de la Teoria de Nodos Funcionales, no como predictor clinico
definitivo.

## Variables nuevas o centrales

- `therapeutic_priority_score`: prioridad relativa de la hipotesis dentro del
  modelo.
- `evidence_confidence_score`: confianza de la evidencia disponible para leer la
  hipotesis.
- `missing_evidence_flags`, procedencia y banderas `*_is_proxy`: limites que
  deben viajar junto con los scores.
- `evolutionary_escape_risk_score`, `paralog_count`, `mobile_context`,
  `hgt_context`, `recombination_context` y `resistance_association`: senales que
  modulan el riesgo evolutivo cuando existen.

## Reglas de interpretacion

| Combinacion | Lectura conservadora |
| --- | --- |
| Score alto / confianza alta | Hipotesis priorizada con soporte relativo mas fuerte; aun requiere validacion externa. |
| Score alto / confianza baja | Hipotesis exploratoria priorizada; revisar proxies, faltantes y procedencia. |
| Score bajo / confianza alta | Baja prioridad relativa bajo reglas actuales; no equivale automaticamente a irrelevancia biologica. |
| Score bajo / confianza baja | Evidencia insuficiente para concluir desde ausencia de prioridad. |
| Alto riesgo evolutivo / baja confianza | Advertencia de escape posible con evidencia evolutiva insuficiente. |
| Bajo riesgo aparente / evidencia insuficiente | Riesgo no resuelto; faltantes y proxies no prueban seguridad ni durabilidad. |

El modo conservador penaliza o advierte sobre evidencia proxy, redundancia alta,
`paralog_count` alto, `mobile_context`, `hgt_context`,
`recombination_context`, `resistance_association` y confianza baja. La subcapa
evolutiva modula esta lectura sin reemplazar funcionalidad, selectividad,
accesibilidad ni evidencia trazable.

## Limitaciones actuales

- Un ranking no valida eficacia clinica, actividad farmacologica ni seguridad.
- Datos incompletos, ausencia de evidencia o proxies no equivalen a bajo riesgo.
- Un score alto no eleva por si mismo la confianza.
- La validacion `user_curated` depende de procedencia revisable y de evidencia
  especifica del organismo o alcance declarado.

## Pasos futuros sugeridos

- Ejecutar la primera corrida real `user_curated` con manifest y workspace
  separados de demo, cache, proxy y `controlled_reference`.
- Revisar por candidato combinaciones de prioridad, confianza, procedencia y
  riesgo evolutivo.
- Decidir despues si el modo conservador necesita una configuracion formal o si
  debe seguir como contrato interpretativo de reportes.
