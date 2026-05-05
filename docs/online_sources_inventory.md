# Inventario de `online_sources.py`

## Estado de control de versiones

En este workspace, `src/nodos_funcionales/online_sources.py` aparece como archivo no rastreado en `git status`. No se borro ni se movio durante esta consolidacion.

## Resumen ejecutivo

`online_sources.py` contiene logica usada por la arquitectura actual de resolucion por capa. No es solo experimental: incluye el punto de entrada `fetch_layer_external_source()` requerido para materializar fuentes externas detras del resolvedor, ademas de proveedores controlados y fallbacks. La decision recomendada es versionarlo completo temporalmente, sin modificar comportamiento, y dividirlo luego en commits pequenos con pruebas de equivalencia.

## Funciones publicas detectadas

- `fetch_layer_external_source(layer_key, workspace, filename, config, provider_name)`
- `fetch_online_source(source, workspace, organism_name, taxon_id, config, mode, refresh_cache=False, no_write_cache=False, replace_existing=False)`

Estas funciones son el contrato operativo mas importante porque el resolvedor por capa debe conectar proveedores externos detras de `fetch_layer_external_source()`.

## Clases detectadas

No se detectaron clases. El archivo esta compuesto por funciones y constantes.

## Constantes detectadas

- `SUPPORTED_ONLINE_SOURCES = {"string", "uniprot"}`
- `THERAPEUTIC_CONTEXT_PROVIDER`
- `THERAPEUTIC_CONTEXT_PROVIDER_V2`
- `THERAPEUTIC_CONTEXT_PROVIDERS`

## Contenido funcional

El archivo concentra varias familias de logica:

- Resolucion de contexto del workspace: organismo, cepa, taxon id.
- Escritura de capas materializadas en `data_external/`.
- Lectura de catalogos curados offline.
- Construccion de capas controladas para contexto terapeutico.
- Construccion de stubs/configurables para homologos humanos.
- Lookup real/parcial de UniProt para homologos humanos.
- Integracion de proveedores reales: UniProt, STRING, InterPro, DEG, VFDB y BV-BRC.
- Fallbacks a cache, stubs, controlados o ausencia trazable.

## Conectores externos detectados

- UniProt: localizacion y lookup de homologos humanos.
- STRING: red funcional.
- InterPro: solapamiento de dominios con hospedero.
- DEG: esencialidad.
- VFDB: virulencia.
- BV-BRC: conservacion entre cepas.
- Catalogos curados offline en `data_external/curated_catalogs`.

## Rutas de cache y datos utilizadas

- Entrada base: `data_raw/*.csv`.
- Materializacion externa: `data_external/<layer>.csv`.
- Cache por resolvedor: `data_cache/<layer>.csv`.
- Catalogos curados: `data_external/curated_catalogs/<layer>/`.
- Cache de proveedor delegada a modulos especificos:
  - STRING: configurada por `online_sources.string.cache_filename`.
  - UniProt: configurada por `online_sources.uniprot.cache_filename`.
  - InterPro, DEG, VFDB, BV-BRC: configuradas en sus secciones respectivas.

## Entradas y salidas principales

Entradas:

- `layer_key`
- `workspace`
- `filename`
- `config`
- `provider_name`
- contexto de organismo desde `results/organism_profile.json`

Salidas:

- diccionarios con `layer_key`, `provider_name`, `source_name`, `path`, `status`, `confidence` y a veces `notes`.
- archivos CSV materializados en `data_external/`.

## Duplicaciones detectadas con `online/`

- Normalizacion de modos: debe consolidarse en `online/provider_modes.py`.
- Procedencia: debe usar `online/provenance.py`.
- Cache status: debe alinearse con `online/cache.py`.
- Mensajes/fallback: debe alinearse con `online/fallback.py`.
- Normalizacion de identificadores: debe alinearse con `online/normalization.py`.

Actualmente no se recomienda reescribir todo de una vez porque `fetch_layer_external_source()` mezcla multiples familias de proveedores y fallback.

## Clasificacion por bloque

| Bloque | Clasificacion | Razon |
| --- | --- | --- |
| `fetch_layer_external_source()` | conservar y cubrir antes de mover | Contrato principal del resolvedor por capa. |
| `fetch_online_source()` | conservar | Despacha STRING/UniProt y mantiene compatibilidad. |
| Catalogos curados | migrar a `online/catalogs.py` | Es logica offline estable y separable. |
| Proveedores controlados terapeuticos | migrar despues de pruebas | No son evidencia externa real; necesitan trazabilidad estricta. |
| Homologos humanos stub/hibrido | cubrir con pruebas antes de mover | Mezcla real lookup, local orthology y fallback stub. |
| Helpers HTTP internos | deprecar tras migracion | STRING/UniProt ya tienen modulos propios; evitar duplicacion futura. |
| Escritura `data_external` | conservar temporalmente | Forma parte del contrato actual de materializacion. |
| Proveedores DEG/VFDB/BV-BRC/InterPro | conservar temporalmente | Son integraciones reales delegadas a modulos especificos. |

## Dependencias internas

- `bvbrc_api.fetch_bvbrc_strain_conservation`
- `deg_api.fetch_deg_essentiality`
- `interpro_api.fetch_interpro_host_annotation`
- `string_api.fetch_string_functional_network`
- `uniprot_api.fetch_uniprot_annotations`
- `vfdb_api.fetch_vfdb_virulence`

Tambien depende de convenciones de `config["layer_resolution"]`, `config["online_sources"]`, `data_raw/`, `data_external/` y del manifiesto de adquisicion.

## Dependencias externas

- `pandas`
- `urllib.request`
- APIs externas indirectas:
  - UniProt
  - STRING
  - InterPro
  - DEG
  - VFDB
  - BV-BRC

## Riesgos de versionarlo completo ahora

- Es grande y mezcla conectores, cache, stubs, proveedores controlados y utilidades.
- Puede introducir ruido de revision si se versiona entero sin dividir responsabilidades.
- Contiene logica experimental/controlada junto con conectores reales, lo que aumenta riesgo de confundir evidencia real con proxy/stub si no se audita por secciones.

## Riesgos de no versionarlo

- `layer_resolver.py` puede depender de un archivo que no queda reproducible en el repositorio.
- Los proveedores reales y fallback no quedan auditables por git.
- Otra maquina o clon limpio podria no poder ejecutar la misma resolucion por capa.
- Se dificulta validar que `source_name`, `retrieval_status`, `confidence` y procedencia se preserven.

## Recomendacion

Versionarlo completo temporalmente en un commit dedicado de infraestructura, sin modificar su contenido funcional, y abrir una fase posterior para dividirlo por familias:

- `online/catalogs.py`
- `online/controlled_context.py`
- `online/human_homologs.py`
- `online/layer_external_sources.py`

La division debe hacerse despues de que `online_sources.py` este bajo control de versiones, para que cada movimiento pueda revisarse como refactor sin cambio funcional.

## Opciones evaluadas

| Opcion | Ventaja | Riesgo | Decision |
| --- | --- | --- | --- |
| Versionarlo completo temporalmente | Reproducibilidad inmediata | Archivo grande y mixto | Recomendado |
| Dividir antes de versionar | Mejor arquitectura final | Sin base git para comparar movimientos | No recomendado ahora |
| Mover a `online/legacy_online_sources.py` | Senala deuda tecnica | Puede romper imports actuales | Posponer |
| Mover a experimental | Aisla codigo incierto | Rompe resolvedor si esta en uso | No recomendado |
| Reemplazar por `online/` existente | Arquitectura limpia | Alto riesgo funcional | Posponer |

## Plan de migracion en commits pequenos

1. Versionar `online_sources.py` tal como esta, con mensaje de commit dedicado.
2. Agregar tests de contrato para `fetch_layer_external_source()` con cache/local/stub sin red.
3. Migrar catalogos curados a `online/catalogs.py`.
4. Migrar proveedores controlados a `online/controlled_context.py`.
5. Migrar homologos humanos a `online/human_homologs.py`.
6. Reemplazar helpers duplicados por `provider_modes.py`, `provenance.py`, `cache.py` y `fallback.py`.
7. Mantener `online_sources.py` como capa de compatibilidad hasta que el resolvedor consuma los modulos nuevos.

## Pruebas minimas antes de dividir

- Resolucion por capa user/cache/external/proxy.
- STRING y UniProt cache-first sin red.
- Fallback stub de homologos humanos.
- Proveedores controlados con confianza limitada.
- Preservacion de `source_name`, `retrieval_status`, `confidence`, `path` y `notes`.

## Decision para esta fase

No se borra, no se mueve y no se reemplaza. Se documenta el riesgo y se consolidan los modulos ya versionados (`online_utils.py`, `provider_modes.py`, `provenance.py`, `string_api.py`, `uniprot_api.py`) con pruebas offline.
