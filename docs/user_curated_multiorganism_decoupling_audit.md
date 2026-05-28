# User-curated multiorganism decoupling audit

## Proposito

Esta auditoria revisa que la validacion portable `user_curated` se mantenga como
flujo multi-organism / multi-organismo. El objetivo es confirmar que el flujo de
usuario no depende conceptual ni tecnicamente de un organismo fijo, snapshots
controlados, datos demo, proxy, cache, online ni `controlled_reference` para
construir evidencia aportada por usuario.

## Alcance auditado

La prueba portable
`tests/test_user_curated_minimal_functional_validation_flow.py` construye un
workspace temporal y define el organismo como dato de entrada del fixture. PAO1,
H37Rv y Corynebacterium pueden aparecer en otras fases como ejemplos, fixtures
o referencias controladas, pero no son defaults obligatorios del flujo
`user_curated`.

El flujo `user_curated` debe aceptar arbitrary organism / organismos arbitrarios
aportados por el usuario. Los identificadores de organismo, cepa o taxonomia son
datos de entrada y no supuestos cientificos fijos.

## Procedencia

La separacion de provenance / procedencia sigue siendo obligatoria:

- `user_curated`
- demo
- proxy
- cache
- online
- `controlled_reference`

demo, proxy, cache, online y `controlled_reference` no equivalen a evidencia
`user_curated`. Tampoco deben presentarse como evidencia directa del usuario ni
elevar la confianza por si mismos.

## Interpretacion

La auditoria conserva conservative interpretation / interpretacion
conservadora. No representa no clinical validation / no validacion clinica ni
no experimental validation / no validacion experimental.

Tambien mantiene la regla no organism-specific default: ningun organismo de
ejemplo debe convertirse en default cientifico del pipeline.

## Cierre

Esta auditoria no modifica `scoring.py`, no cambia la logica cientifica y no
regenera outputs historicos. Su funcion es proteger la intencion central de la
Teoria de Nodos Funcionales: therapeutic prioritization / priorizacion
terapeutica multi-organismo con procedencia trazable y lectura conservadora.
