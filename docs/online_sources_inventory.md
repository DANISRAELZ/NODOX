# Inventario de `online_sources.py`

## Estado de control de versiones

Estado verificado el 2026-05-07:

- `git status --short` no reporta cambios.
- `git diff --ignore-space-at-eol --stat` no reporta diferencias.
- `src/nodos_funcionales/online_sources.py` esta rastreado y sigue siendo parte del contrato operativo del repositorio.

No hay evidencia actual de cambios solo por LF/CRLF que deban separarse de cambios funcionales.

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
- `NETWORK_BLOCKED_MODES = {"offline_only"}`
- `NETWORK_PROVIDERS`

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

- Normalizacion de modos: ya existe en `online/provider_modes.py` y `online_sources.py` la usa para el modo efectivo.
- Procedencia: existe en `online/provenance.py`, pero `online_sources.py` aun devuelve procedencia con diccionarios ad hoc en varios bloques.
- Cache status: existe en `online/cache.py`, pero la mayor parte del estado de cache sigue delegada a conectores especificos o al resolvedor.
- Mensajes/fallback: existe en `online/fallback.py`, pero la logica de fallback operativo todavia vive en `online_sources.py`.
- Normalizacion de identificadores: existe en `online/normalization.py`, pero `online_sources.py` conserva helpers locales de normalizacion de proteinas y slugs de catalogo.

Actualmente no se recomienda reescribir todo de una vez porque `fetch_layer_external_source()` mezcla multiples familias de proveedores y fallback.

## Clasificacion por bloque

| Bloque | Clasificacion | Razon |
| --- | --- | --- |
| `fetch_layer_external_source()` | conservar y cubrir antes de mover | Contrato principal del resolvedor por capa. |
| `fetch_online_source()` | conservar | Despacha STRING/UniProt y mantiene compatibilidad. |
| Catalogos curados | migrar a `online/catalogs.py` | Es logica offline estable y separable. |
| Proveedores controlados terapeuticos | cubrir con pruebas antes de mover | No son evidencia externa real; necesitan trazabilidad estricta. |
| Homologos humanos stub/hibrido | cubrir con pruebas antes de mover | Mezcla real lookup, local orthology y fallback stub. |
| Helpers HTTP internos | deprecar tras migracion | STRING/UniProt ya tienen modulos propios; evitar duplicacion futura. |
| Escritura `data_external` | conservar temporalmente | Forma parte del contrato actual de materializacion. |
| Proveedores DEG/VFDB/BV-BRC/InterPro | conservar temporalmente | Son integraciones reales delegadas a modulos especificos. |

## Contrato operativo y consumidores

| Archivo consumidor | Funcion usada | Tipo de dependencia | Riesgo si se mueve |
| --- | --- | --- | --- |
| `src/nodos_funcionales/layer_resolver.py` | `effective_online_source_mode()`, `fetch_layer_external_source()` | Directa, runtime del resolvedor por capa | Alto: puede impedir materializar `data_external/` y romper procedencia por capa. |
| `fetch_online_data.py` | `SUPPORTED_ONLINE_SOURCES`, `fetch_online_source()` | Directa, CLI manual para STRING/UniProt | Medio: rompe herramienta de auditoria/fetch manual aunque el pipeline principal siga funcionando. |
| `src/nodos_funcionales/online_audit.py` | `fetch_online_source()` | Directa, auditoria online controlada | Medio-alto: rompe comparaciones fresh/cache y validaciones documentadas. |
| `tests/test_online_modes.py` | `fetch_layer_external_source()` y patch del import en `layer_resolver` | Directa, contrato offline y modos | Alto: perderia proteccion contra llamadas de red en modos seguros. |
| `tests/test_layer_resolver.py` | patch de `layer_resolver.fetch_layer_external_source` | Indirecta a traves del resolvedor | Alto: valida que la prioridad user/cache/external no se salte. |
| `tests/test_layer_external_sources.py` | `fetch_layer_external_source()` | Directa, proveedores externos/controlados | Alto: valida salida de cada proveedor y sus fallbacks. |
| `tests/test_string_api.py` | `fetch_online_source()` | Directa, despacho STRING | Medio: afecta compatibilidad del CLI y del wrapper de fuente online. |
| `audit_online_sources.py` | usa `src.nodos_funcionales.online_audit` | Indirecta | Medio: depende de que `online_audit.py` conserve su wrapper hacia `fetch_online_source()`. |
| `src/nodos_funcionales/pipeline.py` | no importa estas funciones directamente | Indirecta via `layer_resolver.resolve_layer_inputs()` | Alto si se rompe el resolvedor; bajo si se mantiene una capa de compatibilidad. |

Conclusion: `online_sources.py` sigue siendo contrato operativo. Cualquier migracion debe conservar imports publicos o introducir wrappers de compatibilidad hasta que todos los consumidores cambien con pruebas.

## Estrategia de congelamiento propuesta

No se migra codigo en esta fase. Los puntos de corte recomendados son:

| Modulo futuro | Responsabilidad | Punto de corte seguro |
| --- | --- | --- |
| `src/nodos_funcionales/online/catalogs.py` | Slugs, candidatos de catalogo y lectura/materializacion de catalogos curados offline. | Extraer primero porque no requiere red y se prueba con CSV locales. |
| `src/nodos_funcionales/online/controlled_context.py` | Capas terapeuticas controladas v1/v2 y host annotation controlado. | Mover despues de pruebas que confirmen reglas, confidence y banderas de incompletitud. |
| `src/nodos_funcionales/online/human_homologs.py` | Stub, ortologia local, lookup humano UniProt y fusion real+stub. | Mover solo tras fijar offline_only, local orthology y fallback stub sin red. |
| `src/nodos_funcionales/online/layer_external_sources.py` | Despacho principal de `fetch_layer_external_source()`. | Ultimo corte; debe conservar el contrato publico y delegar a modulos especializados. |
| `src/nodos_funcionales/online/provider_modes.py` | Modos aceptados y normalizacion. | Ya existe; mantenerlo como fuente unica para nuevos modulos. |
| `src/nodos_funcionales/online/provenance.py` | Diccionarios de procedencia, confidence caps, retrieval/cache status. | Ampliar antes de migrar proveedores para evitar formatos ad hoc nuevos. |
| `src/nodos_funcionales/online/cache.py` | Estados de cache y helpers comunes de lectura/escritura cuando aplique. | Usar solo para utilidades comunes; no reemplazar caches especificos sin pruebas. |
| `src/nodos_funcionales/online/fallback.py` | Mensajes y clasificacion de fallback trazable. | Convertir en helper comun para `missing`, `stub`, `controlled` y `cache`. |

Durante el congelamiento, `src/nodos_funcionales/online_sources.py` debe quedar como fachada estable. Los commits de migracion futuros deben ser refactors sin cambio funcional observable.

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
