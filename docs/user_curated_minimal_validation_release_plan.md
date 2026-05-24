# User-curated minimal validation release plan

## Proposito

Este documento fija el contrato de una futura validacion minima con datos
ingresados por el usuario. La fase es documental y de prueba: no crea datasets
reales, no ejecuta scoring, no modifica `src/nodos_funcionales/scoring.py` y no
genera outputs en `results/`, `data_processed/` ni `data_sessions/`.

El objetivo cientifico es preparar una validacion real minima `user_curated`
que conserve trazabilidad, separacion entre prioridad y confianza, y lectura
terapeutica interpretable sin convertir el sistema en una recomendacion
clinica.

## Alcance de la fase

La validacion minima planificada debe comprobar que Nodos Funcionales puede
recibir datos manuales curados por el usuario sin asumir un organismo modelo
por defecto. El sistema debe seguir siendo multi-organismo y theory-first: la
hipotesis funcional y terapeutica guia la organizacion de evidencia, pero la
evidencia disponible no se infiere cuando falta.

Esta fase no cambia pesos, formulas, ranking, snapshots ni contratos de salida
existentes. Solo documenta el contrato que una fase posterior debera cumplir
antes de permitir una corrida controlada con datos reales.

## Contrato minimo esperado

Una validacion minima `user_curated` debe conservar:

- `dataset_id` propio y trazable, definido para el paquete de datos del
  usuario;
- organismo definido por el usuario, sin asumir PAO1, H37Rv ni
  Corynebacterium por defecto;
- candidatos o genes ingresados manualmente por el usuario;
- `provenance=user_curated` o el equivalente estructural ya aceptado por el
  manifest, manteniendo la procedencia revisable en notas o campos de fuente;
- `evidence_confidence_score` explicito para describir el soporte disponible;
- `therapeutic_priority_score` separado de `evidence_confidence_score`;
- `evolutionary_escape_risk` y variables evolutivas interpretadas como
  moduladores de riesgo, no como certeza clinica;
- advertencia clara de que ausencia o insuficiencia de evidencia no debe
  interpretarse como bajo riesgo;
- separacion estricta entre `demo`, `proxy`, `cache`, `controlled_reference` y
  `user_curated`;
- salida interpretable como priorizacion terapeutica exploratoria, no como
  recomendacion clinica.

## Variables que deben permanecer interpretables

La fase posterior debe preservar variables descomponibles y auditables:

| Variable | Lectura esperada |
| --- | --- |
| `dataset_id` | Identificador trazable del paquete curado por el usuario. |
| `organism` | Organismo o alcance biologico declarado por el usuario. |
| `gene` / `protein_id` / candidato | Entidad ingresada o revisada manualmente. |
| `provenance` | Procedencia curada; no debe mezclar demo, proxy, cache ni referencia controlada como si fueran evidencia del usuario. |
| `evidence_confidence_score` | Confianza en la evidencia disponible para leer el resultado. |
| `therapeutic_priority_score` | Prioridad terapeutica modelada, separada de la confianza de evidencia. |
| `evolutionary_escape_risk` | Modulador de riesgo evolutivo, no certeza clinica ni prediccion definitiva. |
| variables evolutivas | Contexto de riesgo, escape, movilidad, recombinacion o resistencia cuando exista evidencia. |

## Reglas interpretativas

La validacion minima debe mantener reglas conservadoras:

- un score terapeutico alto con baja confianza sigue siendo exploratorio;
- baja evidencia no equivale a bajo riesgo;
- evidencia faltante no descarta un nodo ni reduce automaticamente el riesgo;
- riesgo evolutivo incierto no equivale a bajo riesgo evolutivo;
- variables evolutivas pueden modular la lectura de prioridad, pero no deben
  presentarse como certeza clinica;
- `demo`, `proxy`, `cache`, `controlled_reference` y `user_curated` no son
  categorias equivalentes;
- una salida `user_curated` debe leerse como priorizacion terapeutica
  interpretable, no como recomendacion clinica, diagnostico ni sustituto de
  validacion experimental.

## Separacion de tipos de evidencia

La validacion minima debe evitar conversiones implicitas entre fuentes:

| Tipo | Lectura permitida |
| --- | --- |
| `demo` | Ejemplo operativo o pedagogico, no evidencia real. |
| `proxy` | Aproximacion marcada; util para exploracion, no evidencia directa. |
| `cache` | Copia tecnica de una resolucion previa; requiere procedencia original. |
| `controlled_reference` | Referencia controlada para pruebas o comparacion, no dato ingresado por usuario. |
| `user_curated` | Evidencia aportada o revisada manualmente por el usuario, con trazabilidad. |

## Limites

Este plan no crea datasets reales y no valida eficacia terapeutica,
seguridad clinica ni accionabilidad experimental. Tampoco convierte la
priorizacion en recomendacion clinica.

El sistema debe conservar orientacion multi-organismo. El organismo debe
declararse en los datos o manifest del usuario; no se debe rellenar con PAO1,
H37Rv ni Corynebacterium como default biologico.

## Validacion por pruebas

La prueba asociada a este documento debe verificar que el contrato queda
presente en texto antes de implementar scoring o salidas reales. La prueba no
debe ejecutar modo online, no debe tocar snapshots y no debe escribir en
`results/`, `data_processed/`, `data_sessions/` ni
`config/taxon_resolution_cache.json`.

## Paso futuro sugerido

El siguiente paso logico es implementar una validacion estructural minima sobre
un paquete `user_curated` dedicado, todavia sin cambiar scoring, que compruebe:

- manifest con `dataset_id`, organismo y fuente declarados;
- candidatos manuales alineados entre capas;
- procedencia `user_curated` separada de demo, proxy, cache y
  `controlled_reference`;
- presencia explicita o estado pendiente de `evidence_confidence_score`;
- lectura separada de `therapeutic_priority_score` y confianza;
- advertencias conservadoras sobre faltantes, evidencia insuficiente y riesgo
  evolutivo.
