# User-curated final reporting interpretation closure

## Proposito

Este cierre documenta la validacion interpretativa final de reportes
`user_curated`. La validacion realizada corresponde a interpretacion de
reportes finales: revisa que el lenguaje, las advertencias, los scores y la
procedencia se lean de forma conservadora y trazable.

Este cierre no representa no clinical validation / no validacion clinica y no
representa no experimental validation / no validacion experimental. La
plataforma Nodos Funcionales es una herramienta de priorizacion terapeutica, no
un predictor definitivo ni una herramienta clinica.

## Separacion entre prioridad y confianza

`therapeutic_priority_score` y `evidence_confidence_score` son metricas
distintas:

- `therapeutic_priority_score` expresa prioridad terapeutica relativa dentro de
  las reglas del pipeline.
- `evidence_confidence_score` expresa confianza en la evidencia disponible para
  interpretar esa prioridad.

Un score terapeutico alto no equivale automaticamente a confianza alta. Un
candidato puede estar priorizado por las reglas actuales y, al mismo tiempo,
tener soporte limitado, procedencia incompleta o evidencia pendiente de revision.

## Evidencia insuficiente y riesgo

Insufficient evidence / evidencia insuficiente no debe interpretarse como bajo
riesgo. La ausencia de evidencia, una capa incompleta o un campo sin soporte
externo no prueban seguridad, bajo riesgo biologico, bajo riesgo para el
hospedero ni validez terapeutica.

Por esta razon, los reportes finales deben evitar lecturas como no safe_target,
no clinically_valid y no validated_experimentally. Esas etiquetas no deben
aparecer como conclusiones positivas derivadas del pipeline.

## Alcance de user_curated

`user_curated` representa evidencia aportada o revisada por el usuario. No
equivale automaticamente a evidencia externa verificada automaticamente.

Estados o notas como `pending_review`, `local_note`, `curator_notes`,
`accepted_for_test`, `include_for_structure_check` u otros estados similares
preservan contexto de curacion, pero no deben elevar confianza por si mismos. Un
estado operativo puede explicar por que un candidato fue incluido en una
revision, pero no convierte esa inclusion en validacion clinica, validacion
experimental ni confirmacion externa.

## Lectura conservadora y procedencia

Los reportes finales deben mantener conservative interpretation /
interpretacion conservadora, provenance / procedencia trazable y separacion
explicita entre fuentes:

- `user_curated`
- demo
- proxy
- cache
- online
- `controlled_reference`

La separacion de procedencia evita que datos de demostracion, cache, proxies,
referencias controladas u online se lean como evidencia de usuario. Tambien
evita que evidencia aportada por el usuario se presente como verificacion
externa automatica.

## Cierre

Esta subfase cierra solo la interpretacion documental de reportes finales
`user_curated`. No modifica scoring, reglas cientificas, snapshots ni outputs
generados. La lectura correcta sigue siendo conservadora: prioridad terapeutica,
confianza de evidencia, procedencia y estado de revision deben viajar separados.
