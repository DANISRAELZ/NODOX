# Multi Organism Design

## Principio

La teoria es independiente del organismo. Pseudomonas aeruginosa PAO1,
Corynebacterium pseudotuberculosis u otros organismos pueden usarse como demos,
snapshots o casos de validacion, pero no definen la arquitectura.

## Entrada de datos

El usuario puede aportar datos de cualquier organismo mediante capas CSV en
`data_user/` o `data_raw/`. Las capas obligatorias minimas mantienen el pipeline
ejecutable; las capas opcionales aumentan interpretabilidad y confianza.

## Capas obligatorias y opcionales

Capas base:

- `essentiality`
- `virulence`
- `human_homologs`
- `localization`

Capas opcionales:

- `functional_network`
- `strain_conservation`
- `host_annotation`
- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`
- `evolutionary_escape_risk`
- `redundancy`
- `contextual_essentiality`
- `literature_support`

## Evidencia faltante

La falta de una capa reduce cobertura o confianza, pero no se interpreta como
evidencia negativa. El sistema usa `missing_input`, `insufficient_evidence` o
`inferred_proxy` segun corresponda.

## Snapshots y online

Los snapshots curados sirven para reproducibilidad. Las fuentes online son
opcionales y deben pasar por la arquitectura de resolucion por capa. El modo
offline debe seguir funcionando.

## Evitar sesgo contra organismos poco estudiados

Un organismo con menos literatura o menos conectores reales puede tener menor
confianza, pero no debe ser descartado automaticamente. El ranking debe reportar
que la hipotesis depende de evidencia incompleta.
