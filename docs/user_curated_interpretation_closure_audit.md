# User-curated interpretation closure audit

## Proposito

Esta auditoria cierra la fase interpretativa `user_curated`. Verifica que las
capas recientes de explicacion, modo conservador, matriz final y exportacion
esten documentadas, probadas e integradas como lectura de resultados, sin
modificar el scoring cientifico ni el ranking.

## Componentes auditados

| Componente | Que garantiza |
| --- | --- |
| `score_confidence_interpretation` | Mantiene separadas las dimensiones `therapeutic_priority_score` y `evidence_confidence_score`. Un score alto no equivale a confianza alta, y confianza alta no equivale a prioridad alta. |
| `conservative_interpretation` | Agrega advertencias interpretativas cuando hay baja confianza, evidencia demo/proxy/cache, `controlled_reference`, riesgo evolutivo alto o incierto, evidencia evolutiva insuficiente o procedencia `user_curated` incompleta. |
| `final_interpretation_matrix` | Integra prioridad, confianza, riesgo evolutivo, procedencia y modo conservador en una categoria interpretativa por candidato. |
| Exportacion de `final_interpretation_matrix` | Conserva la matriz final en las explicaciones exportables, incluyendo CSV, Markdown y serializacion JSON desde el DataFrame de explicaciones. |

## Que no cambia

Esta auditoria no modifica:

- `src/nodos_funcionales/scoring.py`;
- pesos;
- formulas;
- logica cientifica central;
- ranking;
- ordenamiento de candidatos;
- snapshots controlados;
- outputs permanentes en `results/`, `data_processed/` ni `data_sessions/`.

Exportar `final_interpretation_matrix` no recalcula scores, no cambia prioridad,
no reordena candidatos y no convierte una hipotesis en candidato confirmado.

## Advertencias obligatorias

Los reportes y explicaciones deben conservar estas advertencias:

- Nodos Funcionales es una plataforma de priorizacion terapeutica, no una
  herramienta clinica ni predictor definitivo.
- Cualquier candidato requiere validacion experimental antes de elevar una
  conclusion.
- Evidencia insuficiente no equivale a bajo riesgo.
- Riesgo evolutivo incierto no equivale a bajo riesgo evolutivo.
- `therapeutic_priority_score` y `evidence_confidence_score` son dimensiones
  distintas.
- Demo, proxy y cache no equivalen a evidencia real.
- `controlled_reference` es referencia controlada, no evidencia de usuario.
- `user_curated` requiere trazabilidad de procedencia.
- Fuentes online deben mantenerse separadas y no mezclarse como evidencia
  `user_curated` sin revision.

## Separacion de procedencia

La interpretacion mantiene separadas estas categorias:

- `user_curated`: evidencia aportada o revisada por el usuario, valida solo si
  conserva procedencia trazable.
- `demo`: datos para probar el flujo, no evidencia biologica real.
- `proxy`: aproximacion o fallback, no observacion directa.
- `cache`: reproduccion o reutilizacion tecnica, no evidencia nueva.
- `controlled_reference`: referencia congelada para contratos, no evidencia de
  usuario.
- `online`: fuente externa fresca que debe entrar por fases o proveedores
  auditables separados.

## Orientacion multiorganismo

La auditoria no depende de un organismo especifico. Los fixtures de cierre usan
identificadores genericos y el flujo sigue orientado a multiples organismos
bacterianos siempre que las capas, procedencia y limitaciones esten declaradas.

## Estado de cierre

La fase queda cerrada si las pruebas verifican que:

- `score_confidence_interpretation`, `conservative_interpretation` y
  `final_interpretation_matrix` existen en las explicaciones;
- la matriz final se conserva al exportar;
- los textos criticos de seguridad interpretativa siguen presentes;
- los scores y el orden del ranking de entrada no cambian;
- la auditoria sigue siendo documental y funcional, no una nueva capa de
  scoring.
