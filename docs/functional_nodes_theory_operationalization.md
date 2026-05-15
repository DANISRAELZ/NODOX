# Operacionalizacion de la Teoria de Nodos Funcionales

## Proposito del documento

Este documento explica como el proyecto Nodos Funcionales convierte la Teoria de Nodos Funcionales en un pipeline computacional auditable. La finalidad del software no es centrarse en un organismo, una base de datos, un snapshot, un importador o una consulta online. Todas esas piezas existen para operacionalizar, probar, validar y explicar la teoria.

## Principio rector

La priorizacion terapeutica no parte de un organismo especifico. Parte de identificar nodos funcionales cuya perturbacion pueda afectar procesos criticos del patogeno con el menor dano posible al hospedero, manteniendo trazabilidad sobre la procedencia, calidad y suficiencia de la evidencia.

## Postulados operacionales de la teoria

1. Un blanco terapeutico debe evaluarse como nodo funcional dentro de una red biologica, no solo como gen aislado.
2. La prioridad terapeutica depende de integrar esencialidad, conectividad, conservacion, localizacion, virulencia, impacto clinico, dano al hospedero y contexto terapeutico.
3. Los hubs, bottlenecks y reguladores globales pueden tener impacto sistemico, pero requieren evaluacion de selectividad y riesgo de toxicidad.
4. La evidencia debe ponderarse por procedencia, calidad, especificidad y actualidad.
5. La robustez evolutiva y la restriccion del escape son componentes centrales: un nodo terapeutico debe evaluarse por la facilidad con que el patogeno podria evadir la perturbacion mediante mutacion, redundancia, movilidad genetica, recombinacion o asociacion con resistencia.
6. La ausencia de evidencia no debe interpretarse como evidencia negativa.

## Traduccion de postulados a capas computacionales

| Postulado teorico | Capa computacional | Archivo o modulo relacionado | Tipo de evidencia | Riesgo de sobreinterpretacion | Control implementado |
| --- | --- | --- | --- | --- | --- |
| Nodo funcional, no gen aislado | `functional_network` | `src/nodos_funcionales/scoring_components.py`, `data_templates/functional_network.csv` | Red funcional, STRING, red de usuario o proxy declarado | Confundir proxy o red incompleta con conectividad real | Procedencia, `retrieval_status`, confianza por capa |
| Integracion multicapa | `essentiality`, `virulence`, `localization`, `clinical_impact`, `therapy_site_context` | `src/nodos_funcionales/integration.py`, `src/nodos_funcionales/scoring.py` | Datos de usuario, snapshots, fuentes externas o plantillas | Ranking fuerte con capas ausentes | Validacion de columnas, defaults explicitos y reportes |
| Selectividad y dano al hospedero | `human_homologs`, `host_damage` | `data_templates/human_homologs.csv`, scoring terapeutico | Homologia, riesgo al hospedero, anotacion curada | Asumir seguridad por falta de homologo documentado | `missing_input` e `insufficient_evidence` no se tratan como seguridad |
| Evidencia ponderada | provenance/confidence | `src/nodos_funcionales/layer_resolver.py`, `src/nodos_funcionales/config.py` | Metadatos de fuente y confianza | Mezclar demo, cache, usuario y fuente real | Jerarquia de evidencia y campos `<layer>_source_*` |
| Robustez evolutiva y restriccion del escape | `strain_conservation`, `evolutionary_escape_risk`, `evolutionary_constraint` | `src/nodos_funcionales/evolutionary_escape_risk.py`, `src/nodos_funcionales/generic_annotation_import.py`, `data_templates/evolutionary_escape_risk_template.csv` | Conservacion, tolerancia mutacional, redundancia, paralogia, movilidad, HGT, recombinacion, resistencia | Inventar bajo o alto riesgo sin evidencia local o externa suficiente | Estados `unknown`, `missing_input`, `insufficient_evidence`, `not_detected_with_method`, `detected`; penalizacion moderada y auditable |
| Ausencia no negativa | Todas las capas | Validacion, normalizacion y reporting | Datos faltantes o parciales | Convertir no observado en no existente | Estados `missing_input` e `insufficient_evidence` |
| Contexto terapeutico | `curated_disease_context`, `therapy_site_context`, `literature_support` | `data_templates/`, `src/nodos_funcionales/reporting.py` | Curacion clinica, sitio de infeccion, bibliografia | Generalizar fuera del contexto reportado | Resumen de limitaciones y soporte bibliografico separado |

## Postulado 5: robustez evolutiva y restriccion del escape

La capa evolutiva es uno de los elementos distintivos de la Teoria de Nodos Funcionales. La teoria no pregunta solo si un nodo parece importante hoy; pregunta tambien si la perturbacion de ese nodo podria sostener presion terapeutica sin abrir una ruta facil de escape evolutivo.

`evolutionary_escape_risk` es la estimacion del riesgo de que el patogeno evada la perturbacion terapeutica sobre un nodo funcional. Aumenta cuando hay senales de tolerancia mutacional, redundancia funcional, paralogos compensatorios, movilidad genetica, transferencia horizontal, recombinacion o asociacion con mecanismos de resistencia.

`evolutionary_constraint` es la estimacion de restriccion evolutiva que limita el espacio de escape del nodo. Aumenta cuando el nodo parece conservado, poco redundante, poco movil, dificil de reemplazar, central para procesos criticos o con baja tolerancia mutacional documentada.

Estas variables no son accesorios del scoring. Forman parte vital del Postulado 5 porque distinguen entre un blanco que solo parece atractivo por esencialidad o virulencia y un nodo cuya perturbacion podria ser mas robusta frente a adaptacion evolutiva.

### Variables centrales

- `evolutionary_escape_risk`: riesgo agregado de escape. Alto significa mayor probabilidad teorica de evasion bajo presion terapeutica.
- `evolutionary_constraint`: restriccion evolutiva agregada. Alto significa menor espacio de escape esperable, siempre que la evidencia sea suficiente.
- `mutation_tolerance`: capacidad del nodo para acumular variacion sin perder funcion biologica relevante.
- `pathway_redundancy`: existencia de rutas alternativas que puedan compensar la inhibicion del nodo.
- `paralog_count`: numero de genes paralogos o copias funcionalmente relacionadas que podrian sustituir o amortiguar el efecto.
- `mobile_context`: senal de que el nodo se ubica en contexto movil, plasmidico, transponible o asociado a elementos geneticos moviles.
- `hgt_context`: senal de transferencia horizontal o adquisicion desde fuentes externas.
- `recombination_context`: senal de recombinacion, intercambio alelico o regiones con variabilidad recombinante.
- `resistance_association`: relacion directa o indirecta con resistencia, escape farmacologico, bombas, modificacion de blanco o funciones que facilitan supervivencia bajo tratamiento.

### Mapa variable, pregunta biologica y efecto esperado

| Variable | Pregunta biologica | Efecto en `evolutionary_escape_risk` | Efecto en `evolutionary_constraint` |
| --- | --- | --- | --- |
| `mutation_tolerance` | El nodo tolera mutaciones sin perder funcion critica? | Aumenta si la tolerancia es alta. | Disminuye si la tolerancia es alta. |
| `pathway_redundancy` | Existe una ruta alternativa que compense la perturbacion? | Aumenta si hay redundancia funcional. | Disminuye si la compensacion es plausible. |
| `paralog_count` | Hay paralogos que puedan amortiguar la perdida del nodo? | Aumenta cuando hay multiples copias o paralogos funcionales. | Disminuye si los paralogos son plausiblemente compensatorios. |
| `mobile_context` | El nodo esta en contexto movil o transferible? | Aumenta si el contexto movil esta detectado. | Disminuye porque la estabilidad del nodo como blanco es menor. |
| `hgt_context` | Hay senales de transferencia horizontal? | Aumenta si el nodo podria adquirirse, perderse o reemplazarse por HGT. | Disminuye si la evidencia sugiere plasticidad genetica. |
| `recombination_context` | El nodo o su region muestran recombinacion relevante? | Aumenta si la recombinacion facilita variantes de escape. | Disminuye si la region no esta evolutivamente restringida. |
| `resistance_association` | El nodo esta asociado a resistencia o supervivencia bajo tratamiento? | Aumenta si hay asociacion directa o funcional. | Disminuye salvo que exista evidencia de restriccion fuerte pese a esa asociacion. |
| `evolutionary_constraint` | El nodo parece dificil de modificar o reemplazar? | Disminuye el riesgo cuando la restriccion es alta y confiable. | Aumenta por definicion. |

### Estados de interpretacion

| Estado | Interpretacion | Regla |
| --- | --- | --- |
| `unknown` | El estado biologico no puede determinarse con la evidencia disponible. | Mantener como desconocido; no convertir en bajo ni alto riesgo. |
| `missing_input` | Falta el archivo, capa o fuente necesaria. | No penalizar como evidencia negativa; reportar la ausencia. |
| `insufficient_evidence` | Hay datos parciales, pero no alcanzan para afirmar presencia o ausencia. | Usar confianza baja y evitar conclusiones fuertes. |
| `not_detected_with_method` | Un metodo concreto busco la senal y no la detecto. | Puede reducir el riesgo solo de forma limitada y especifica al metodo, nunca como ausencia universal. |
| `detected` | La senal fue detectada por una fuente declarada. | Puede aumentar riesgo o restriccion segun la variable, ponderado por procedencia y confianza. |

La ausencia de movilidad, HGT, recombinacion, resistencia o paralogos en una fuente incompleta no equivale a demostrar que esos factores no existen. Solo `not_detected_with_method`, acompanado del metodo y su alcance, permite una interpretacion negativa parcial.

### Efecto sobre el score final

La capa evolutiva modifica el ranking mediante dos fuerzas complementarias:

```text
mayor evolutionary_escape_risk -> penalizacion moderada del candidato
mayor evolutionary_constraint  -> soporte teorico para robustez del candidato
```

En la implementacion actual, `evolutionary_escape_risk_score` puede actuar como penalizacion moderada y configurable sobre la prioridad final, mientras que `evolutionary_constraint_score` contribuye a interpretar por que un nodo podria tener menor espacio de escape. Esta penalizacion no debe eliminar automaticamente candidatos: debe bajar prioridad, reducir confianza o activar auditoria cuando el riesgo sea alto o la evidencia sea insuficiente.

El reporte final debe exponer al menos el riesgo, la restriccion, la confianza, las variables disponibles y las variables faltantes. Asi, un candidato no queda castigado por ignorancia del sistema, sino interpretado con cautela.

## Jerarquia de evidencia

El pipeline debe priorizar la evidencia en este orden interpretativo:

`user_supplied > curated_snapshot > real_external_online > controlled_provider > inferred_proxy > demo > missing_input`

- `user_supplied`: datos cargados explicitamente por el usuario.
- `curated_snapshot`: referencia controlada y versionada.
- `real_external_online`: consulta real a una fuente externa.
- `controlled_provider`: proveedor controlado interno u offline.
- `inferred_proxy`: inferencia aproximada, util pero de menor peso.
- `demo`: ejemplo tecnico sin valor como evidencia real.
- `missing_input`: falta de entrada.
- `insufficient_evidence`: evidencia parcial que no alcanza para afirmar una conclusion.

Regla critica: `missing_input` e `insufficient_evidence` nunca deben convertirse automaticamente en evidencia negativa.

## Papel de los organismos ejemplo

Organismos como `Pseudomonas aeruginosa` PAO1, `Corynebacterium pseudotuberculosis`, `Mycobacterium tuberculosis` H37Rv o `Helicobacter pylori` pueden aparecer como casos de validacion, demostracion o control tecnico.

Los organismos utilizados en ejemplos o snapshots cumplen una funcion de validacion tecnica y demostracion multi-organismo. No definen el alcance conceptual del proyecto. El alcance conceptual esta definido por la Teoria de Nodos Funcionales.

## Papel de la consulta online

UniProt, STRING y otras fuentes no son el objetivo del proyecto. Son proveedores de evidencia para alimentar capas de la teoria. La consulta online debe ser opcional, auditable, cacheable cuando sea posible, marcada por procedencia y subordinada al modelo teorico.

## Papel de los snapshots

Los snapshots no son verdad biologica absoluta. Son referencias controladas para pruebas, reproducibilidad, comparacion, auditoria y validacion tecnica. Un snapshot puede ayudar a comprobar que el pipeline conserva contratos de datos, pero no sustituye evidencia especifica del usuario ni validacion experimental.

## Papel de los importadores

Los importadores no son el nucleo del proyecto. Son mecanismos para convertir datos del usuario o anotaciones locales en capas computacionales compatibles con la Teoria de Nodos Funcionales. Deben preservar procedencia, ausencia de evidencia y compatibilidad con la resolucion por capas.

## Relacion teoria, scoring y ranking

```text
Teoria de Nodos Funcionales
  -> capas de evidencia
  -> normalizacion
  -> pesos y confianza
  -> scoring
  -> ranking
  -> explicacion por candidato
  -> auditoria cientifica
```

El ranking final es una salida interpretativa del modelo, no una validacion biologica definitiva. La teoria guia la priorizacion y ayuda a ordenar hipotesis computacionales, pero no confirma eficacia terapeutica ni produce recomendaciones clinicas. Cada candidato debe poder explicarse por las capas que lo favorecen, las que lo limitan y las fuentes que sostienen esas senales.

## Limitaciones

- Datos incompletos producen rankings parciales o ejecuciones detenidas por validacion.
- La evidencia online general no sustituye datos especificos cargados por el usuario.
- Los snapshots demo no sustituyen evidencia real.
- El scoring debe evitar sobreinterpretar proxies o ausencia de datos.
- Cada ranking debe reportar procedencia, confianza, limitaciones y capas insuficientes.
- Toda aplicacion requiere validacion experimental y clinica externa.
