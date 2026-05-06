# AGENTS.md

## Working style

\# AGENTS.md



\## Propósito del repositorio

Este repositorio implementa un pipeline reproducible para la identificación, integración y priorización terapéutica de nodos funcionales bacterianos a partir de bases de datos curadas. No debe reinventarse la arquitectura desde cero. Los cambios deben extender el pipeline actual de forma conservadora, compatible y auditable.



\## Principios obligatorios

1\. No crear un proyecto nuevo si ya existe una estructura funcional.

2\. No reescribir módulos completos sin justificación fuerte.

3\. Reutilizar funciones, utilidades y convenciones existentes antes de duplicar lógica.

4\. Mantener compatibilidad hacia atrás con los outputs actuales siempre que sea posible.

5\. Priorizar reproducibilidad, trazabilidad e interpretabilidad por encima de complejidad o “inteligencia” aparente.

6\. No introducir dependencias innecesarias.

7\. No inventar datos ni simular evidencia científica no presente.

8\. Si faltan columnas o datos, usar valores por defecto explícitos y marcar la incompletitud.

9\. Todo cambio debe quedar documentado en código y en Markdown.

10\. Cualquier score nuevo debe ser interpretable y descomponible por variables.



\## Arquitectura a respetar

El pipeline actual ya incluye módulos con responsabilidades separadas:

\- discovery

\- acquisition

\- validation

\- normalization

\- integration

\- scoring

\- reporting

\- config/runtime

\- online sources opcionales



La orquestación principal ya existe. Los cambios deben integrarse a esta arquitectura, no reemplazarla.



\## Objetivo de la fase actual

Implementar una primera expansión científica del sistema para incorporar nuevas consideraciones terapéuticas en la priorización de nodos funcionales, especialmente:

\- daño potencial al hospedero

\- accesibilidad/permeabilidad en el sitio de infección

\- relevancia contextual durante la infección

\- clasificación del rol terapéutico del nodo



\## Restricciones de esta fase

No agregar:

\- interfaz gráfica

\- dashboard

\- API

\- deep learning

\- reescritura completa del pipeline

\- dependencias pesadas no justificadas

\- consultas online obligatorias para que la fase funcione



\## Nuevas variables esperadas

Agregar o extender, de forma mínima y compatible, variables como:

\- host\_damage\_score

\- infection\_site\_access\_score

\- infection\_context\_score

\- therapeutic\_role

\- therapeutic\_priority\_score



\## Clasificaciones esperadas para therapeutic\_role

\- bactericidal\_candidate

\- antivirulence\_candidate

\- sensitizer\_candidate

\- mixed\_strategy\_candidate

\- low\_priority\_candidate



\## Estrategia de implementación

1\. Inspeccionar primero qué partes del pipeline ya contienen señales parecidas.

2\. Extender primero scoring, integration, reporting y config.

3\. Crear helpers nuevos solo si son pequeños y claramente necesarios.

4\. Mantener las reglas transparentes y heurísticas en esta fase.

5\. Evitar cambios grandes en nombres, rutas y contratos de datos.

6\. Proponer mejoras considerables al terminar la iteracióno proponer paso lógico siguiente para lograr el objetivo del proyecto



\## Reglas científicas iniciales

Las reglas nuevas deben ser transparentes, por ejemplo:

\- alta esencialidad + buena accesibilidad + bajo riesgo al hospedero => bactericidal\_candidate

\- alta virulencia + bajo riesgo al hospedero + accesibilidad aceptable => antivirulence\_candidate

\- señal moderada no letal pero útil para potenciar tratamientos => sensitizer\_candidate

\- combinación fuerte de varias dimensiones => mixed\_strategy\_candidate

\- evidencia insuficiente o alto riesgo => low\_priority\_candidate



\## Convenciones de trabajo

\- Explicar cambios como si el usuario no fuera programador.

\- Dar primero plan corto antes de modificar archivos grandes.

\- Mostrar lista de archivos a cambiar.

\- Entregar código completo cuando se modifique un archivo.

\- No omitir bloques de código con frases como “rest omitted”.

\- Añadir comentarios claros en código nuevo.

\- Mantener nombres explícitos y legibles.



\## Validación mínima esperada

Cada cambio debe:

\- conservar la ejecución del pipeline

\- producir outputs legibles

\- mantener trazabilidad de scores

\- documentar nuevas columnas y reglas

\- evitar romper reportes existentes sin avisar



\## Documentación obligatoria

Cada fase nueva debe incluir un archivo Markdown en docs/ con:

\- propósito científico

\- variables nuevas

\- reglas de scoring

\- limitaciones actuales

\- pasos futuros sugeridos



\## En caso de duda

Elegir siempre la opción:

\- más simple

\- más compatible

\- más reproducible

\- más interpretable

## Estado actual de la arquitectura
El repositorio ya implementa una capa de resolución por dataset antes de validación:
- `layer_registry.py`
- `layer_resolver.py`

Cada capa puede resolverse desde:
1. `data_user/`
2. `data_cache/`
3. `data_external/`
4. proxy/default explícito

No se debe bypassar esta arquitectura al añadir nuevas fuentes externas.

## Regla para nuevas integraciones externas
Toda conexión a una base externa real debe implementarse detrás de `fetch_layer_external_source()` o helpers equivalentes, manteniendo el contrato actual del resolvedor.

## Prioridad de fuentes
Las estrategias configurables por capa (`user_preferred`, `external_preferred`, `merge_with_priority`) deben preservarse. No se debe imponer una prioridad global nueva sin cambiar la configuración.

## Procedencia obligatoria
Toda capa resuelta debe conservar y propagar:
- `<layer>_source_type`
- `<layer>_source_name`
- `<layer>_is_user_supplied`
- `<layer>_is_external`
- `<layer>_is_cached`
- `<layer>_is_proxy`
- `<layer>_confidence`
- `<layer>_retrieval_status`

## Restricción para la siguiente fase
La siguiente fase debe conectar proveedores reales de forma incremental, empezando por capas con fuente natural y estable, sin intentar conectar todas las bases a la vez.

## Estado actual de proveedores por capa

La arquitectura de resolución por capa ya está implementada y debe respetarse.

Estado actual:
- `localization` usa un proveedor real basado en UniProt.
- `functional_network` usa un proveedor real basado en STRING y materializa `data_external/functional_network.csv`.
- `human_homologs` sigue como `configurable_stub`, con confianza baja y marcado explícito.

## Reglas de integración externa

1. No cambiar el contrato de `layer_resolver.py` sin justificación fuerte.
2. Toda nueva fuente externa debe integrarse detrás del resolvedor actual.
3. Deben preservarse `source_name`, `retrieval_status` y `confidence`.
4. En capas `user_preferred`, si ya existe un `data_raw/` válido, no consultar el proveedor externo innecesariamente.
5. No reemplazar proveedores reales existentes por stubs o lógica ad hoc.