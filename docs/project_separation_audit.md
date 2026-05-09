# Auditoria de separacion de proyectos

Fecha: 2026-05-08

## Estado inicial

`git status --short` mostro cambios previos sin commitear en `.gitignore`, snapshots PAO1, documentacion multi-organismo, `src/nodos_funcionales/curated_snapshots.py`, `tests/test_curated_snapshots.py`, y archivos nuevos ligados a la fase previa `cpseudo_*`.

Se intento crear la rama `codex/project-separation-online-enrichment`, pero Git no pudo por conflicto con el ref `codex`. Se creo en su lugar `codex-project-separation-online-enrichment`.

## Referencias encontradas

| Archivo o ruta | Linea/seccion | Referencia encontrada | Tipo de problema | Recomendacion | Riesgo |
|---|---|---|---|---|---|
| `docs/cpseudo_mexico_real_data_audit.md` | nombre y contenido | `cpseudo_mexico`, Mexico, datos reales de aislados | documentacion mezclada | borrar y reemplazar por documentacion generica | bajo |
| `docs/cpseudo_mexico_real_data_import.md` | nombre y contenido | importacion C. pseudotuberculosis biovar ovis Mexico | documentacion mezclada | borrar y reemplazar por importacion generica | bajo |
| `docs/cpseudo_mexico_import_status.md` | nombre y contenido | estado de importacion Mexico | documentacion mezclada | borrar y reemplazar por estado general | bajo |
| `src/nodos_funcionales/cpseudo_import.py` | nombre del modulo | importador especifico `cpseudo` | codigo acoplado por nombre | renombrar a `generic_annotation_import.py` | medio |
| `import_dataset.py` | import y CLI | `cpseudo_annotations` | nombre incorrecto | renombrar formato a `generic_annotations` y retirar el alias especifico | medio |
| `tests/test_cpseudo_import.py` | nombre del test | `cpseudo` | fixture de prueba mal nombrado | renombrar a `test_generic_annotation_import.py` | bajo |
| `tests/fixtures/cpseudo_annotations/` | ruta | `cpseudo_annotations` | fixture de prueba mal nombrado | mover a `tests/fixtures/generic_organism_annotations/` | bajo |
| `data_sessions/cpseudo_mexico/` | ruta ignorada por git | sesion mexicana | sesion de trabajo no necesaria | no usar en documentacion operativa; preferir workspace generico nuevo | bajo si queda ignorado |
| `data_sessions/cpseudo_demo/` | ruta ignorada por git | demo cpseudo | nombre ambiguo | no referenciar; si se necesita, usar demo generico | bajo |
| `data_sessions/cpseudo_online_optional/` | ruta ignorada por git | online cpseudo | nombre ambiguo | no referenciar; nuevo ejemplo debe usar `corynebacterium_pseudotuberculosis_online_demo` | bajo |
| `data_external/curated_snapshots/corynebacterium_pseudotuberculosis_biovar_ovis/` | snapshot | C. pseudotuberculosis biovar ovis | snapshot ambiguo | conservar solo si metadata indica fixture controlado generico, no aislados mexicanos ni evidencia real | medio |

## Busquedas realizadas

Terminos auditados por contenido y rutas:

- `cpseudo_mexico`
- `mexico`, `mexicanos`, `mexican`
- `aislados`, `isolates`, `17 isolates`
- `Corynebacterium mexican isolates`
- `pangenome mexicano`
- `biovar ovis mexican`
- `data_sessions/cpseudo_mexico`
- `cpseudo_mexico_real_data`
- `cpseudo_mexico_import`
- `cpseudo_annotations`
- `Corynebacterium pseudotuberculosis biovar ovis`

## Principio aplicado

Corynebacterium pseudotuberculosis puede mantenerse como ejemplo generico multi-organismo o caso de consulta online. Ningun archivo operativo debe sugerir que Nodos Funcionales usa datos del proyecto independiente de aislados mexicanos.
