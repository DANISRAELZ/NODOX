# User-Curated Controlled Scoring Specification

## Estado de esta especificacion

Esta nota define un modo futuro y conservador de scoring controlado para
datasets `user_curated`. No implementa scoring, no ejecuta pipeline y no genera
rankings en la fase actual.

## Proposito

El scoring controlado `user_curated` solo deberia permitirse bajo condiciones
explicitas. Su proposito futuro es:

- evitar que datos incompletos, demo, proxy o de baja procedencia generen
  priorizaciones enganosas;
- conservar separacion entre `therapeutic_priority_score` y
  `evidence_confidence_score`;
- dejar claro que un score alto no equivale automaticamente a confianza alta;
- dejar claro que scoring no equivale a validacion biologica, validacion
  clinica ni recomendacion terapeutica.

El modo futuro debe seguir siendo multiorganismo: organismo y strain o linea
deben venir del usuario, sin defaults ocultos de organismo o cepa.

## Estados de entrada

| Estado | Significado conservador |
| --- | --- |
| `not_ready_for_scoring` | Hay bloqueos estructurales o de completitud que impiden avanzar. |
| `requires_expert_review` | El paquete necesita decision experta antes de cualquier scoring futuro. |
| `conditionally_ready_for_future_controlled_scoring` | El quality gate permite preparar una aprobacion manual futura, pero no habilita ranking por si solo. |
| `approved_for_controlled_scoring` | Existe aprobacion manual documentada para una corrida controlada futura bajo los limites de esta especificacion. |

`conditionally_ready_for_future_controlled_scoring` no se transforma
automaticamente en `approved_for_controlled_scoring`.

## Criterios minimos para aprobacion

`approved_for_controlled_scoring` requiere como minimo:

1. `manifest.csv` valido;
2. `dataset_id` explicito;
3. organismo y strain o linea definidos por el usuario, sin defaults;
4. archivos minimos presentes para las variables criticas declaradas;
5. ausencia de placeholders activos;
6. `provenance` explicita y trazable;
7. `evidence_status` compatible con evidencia `user_curated` revisada;
8. ausencia de marcas demo, proxy o cache como evidencia principal;
9. revision experta documentada;
10. aprobacion manual registrada;
11. advertencias evolutivas revisadas antes de interpretar la corrida futura.

La aprobacion debe registrar quien reviso, fecha, alcance, limites aceptados,
advertencias pendientes y la version del manifest revisado.

## Bloqueos absolutos

No ejecutar scoring sin aprobacion manual. No generar rankings sin revision
experta.

Son bloqueos absolutos:

- errores estructurales;
- placeholders activos;
- organismo ausente o ambiguo;
- mezcla de `user_curated` con demo, proxy o cache sin declaracion;
- `evidence_status=pending` como evidencia principal;
- `provenance` ausente;
- datos insuficientes para variables criticas;
- intento de generar ranking sin aprobacion manual;
- ausencia de revision experta.

Cuando exista un bloqueo absoluto, el estado no puede ser
`approved_for_controlled_scoring`.

## Reglas conservadoras para interpretacion futura

- Ausencia de evidencia no equivale a bajo riesgo.
- Evidencia incompleta debe reducir confidence, no inflar prioridad.
- Datos proxy no deben equivaler a datos `user_curated`.
- Datos demo no deben ser usados como evidencia real.
- Cache no debe presentarse como evidencia real si solo reproduce una capa o
  consulta previa.
- `high therapeutic_priority_score` junto con
  `low evidence_confidence_score` debe requerir revision.
- `high evolutionary_escape_risk` debe advertirse aunque el score funcional
  sea alto.
- `mobile_context`, `hgt_context`, `recombination_context` y
  `resistance_association` deben modular la interpretacion.

La confianza de evidencia y la prioridad terapeutica futura deben poder
explicarse por separado.

## Tabla interpretativa futura

| Combinacion futura | Lectura minima |
| --- | --- |
| Score alto / confianza alta | Hipotesis priorizada para revision experta; no es validacion terapeutica. |
| Score alto / confianza baja | Prioridad aparente con evidencia debil; revisar faltantes y procedencia antes de interpretar. |
| Score bajo / confianza alta | Evidencia trazable para baja prioridad relativa dentro del modelo y alcance revisados. |
| Score bajo / confianza baja | Lectura debil; no concluir ausencia biologica ni bajo riesgo. |
| Score alto / riesgo evolutivo alto | Advertir escape o resistencia potencial aun con senal funcional alta. |
| Score alto / evidencia incompleta | Reducir confianza y documentar variables faltantes antes de cualquier conclusion. |
| No evaluable por evidencia insuficiente | Bloquear lectura comparativa hasta obtener evidencia minima o declarar la limitacion. |

## Separacion de tipos de fuente

`user_curated`, demo, proxy, cache, `controlled_reference` y online no son
intercambiables. El modo futuro debe conservar su procedencia en inputs,
auditorias y reportes interpretativos.

- demo sirve para probar software, no como evidencia real;
- proxy conserva una aproximacion declarada, no reemplaza curacion del usuario;
- cache conserva reproducibilidad o recuperacion previa, no cambia el tipo de
  evidencia;
- `controlled_reference` verifica contratos separados;
- online debe usarse solo bajo modos y workspaces auditables cuando aplique.

## Lo que el modo futuro NO debe hacer

No usar cache, demo o proxy como evidencia real.

El modo de scoring controlado no debe:

- recomendar tratamientos;
- sustituir validacion experimental;
- afirmar utilidad clinica;
- mezclar organismos;
- usar defaults ocultos;
- convertir automaticamente quality gate favorable en ranking;
- tratar cache, demo o proxy como evidencia real.

Tampoco debe ocultar evidencia insuficiente detras de un numero de prioridad.

## Paso de diseno siguiente

Antes de implementar esta especificacion, una fase separada deberia definir:

- el artefacto de aprobacion manual que produce
  `approved_for_controlled_scoring`;
- las variables criticas minimas por capa y por estrategia terapeutica;
- la forma de bloquear CLI, reportes o exportaciones de ranking cuando falte
  aprobacion;
- la trazabilidad esperada entre manifest, revision experta, confidence y
  scoring futuro.
