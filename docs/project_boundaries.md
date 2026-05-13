# Limites del proyecto

## Enfoque conceptual

El eje del repositorio es la Teoria de Nodos Funcionales. La arquitectura
multi-organismo, los ejemplos, snapshots, conectores online, importadores,
pruebas y reportes existen para operacionalizar y auditar esa teoria, no para
convertir ningun organismo o fuente de datos en el centro conceptual.

## Separacion de proyectos

El proyecto Nodos Funcionales es una plataforma multi-organismo para priorizacion de blancos terapeuticos. No depende de colecciones particulares de aislados ni de proyectos genomicos externos.

Cualquier organismo mencionado en ejemplos, incluyendo Corynebacterium pseudotuberculosis, se utiliza unicamente como caso de prueba, demostracion del flujo multi-organismo o consulta online general, salvo que el usuario cargue explicitamente datos propios en un workspace.

## Uso correcto de ejemplos

- PAO1 puede mantenerse como ejemplo historico y control de regresion.
- Corynebacterium pseudotuberculosis puede usarse como organismo ingresado por el usuario o ejemplo de consulta online.
- Los datos de usuario deben entrar por `data_user/`, `data_raw/`, importacion generica o conectores documentados.
- Los fixtures de `tests/fixtures/` no son evidencia cientifica y no deben presentarse como resultados reales.

## Evidencia y procedencia

La prioridad interpretativa esperada es:

`user_supplied > curated_snapshot > real_external_online > controlled_provider > inferred_proxy > demo > missing_input`

`missing_input` e `insufficient_evidence` significan que falta informacion suficiente. No deben convertirse en ceros biologicos absolutos.
