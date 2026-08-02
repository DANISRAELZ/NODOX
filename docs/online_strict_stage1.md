# Online strict: primera etapa de endurecimiento

## Propósito científico

Separar una validación basada sólo en proveedores externos de una ejecución híbrida que también incorpora evidencia curada local. La separación evita atribuir a una consulta online evidencia que en realidad procede de `data_curated/organisms`.

## Modos y procedencia

- `online_strict`: permite el transporte online existente, pero desactiva la carga de `data_curated/organisms`. El manifiesto curado declara `disabled_by_online_strict_policy` y contadores de aplicación en cero.
- `hybrid_curated`: permite y declara la evidencia curada local.
- Los modos históricos (`online_optional`, `cache_first`, `offline_only` y aliases) conservan su comportamiento configurado para compatibilidad.
- `online_only` se acepta como alias de política estricta.

Las opciones públicas, aliases y reglas de canonicalización se definen en
`src/nodos_funcionales/online/provider_modes.py`. Los runners y la capa
compatible `online_utils.py` consumen ese contrato común para evitar que el
parser acepte un modo que luego rechacen los proveedores.

Los proveedores BV-BRC, DEG, human essentiality, InterPro y VFDB también
normalizan ahora mediante ese contrato central. STRING y UniProt conservan sus
constantes públicas por compatibilidad, pero las derivan de las mismas choices.

## Auditoría de proveedores

La auditoría distingue:

- `connectivity_success`: hubo comunicación satisfactoria con el proveedor.
- `retrieval_success`: se recuperaron registros.
- `mapping_success`: al menos un registro se mapeó a candidatos.
- `usable_evidence`: el mapeo aporta evidencia interpretable para la capa.
- `affects_score`: la evidencia se usa en scoring; esta etapa no cambia su política ni sus pesos.

Una respuesta HTTP de STRING sin mapeos utilizables queda degradada y no constituye evidencia utilizable. UniProt usado sólo para crear el conjunto de candidatos tampoco constituye evidencia de esencialidad.

La procedencia distingue además `technical_success` de conectividad HTTP. Un
DIAMOND local ejecutado con resultados y mapeos puede aportar evidencia
utilizable y afectar scoring aunque `api_attempted=false`, mientras que STRING
con HTTP correcto pero sin mapeos conserva éxito técnico y estado degradado.

En `online_strict`, `controlled_therapeutic_context` no puede materializar
`clinical_impact`, `curated_disease_context` ni `therapy_site_context`, ni
activar sus proxies. La opción de materializar fallbacks requeridos se rechaza
porque produciría una salida incompatible con la etiqueta estricta.

`affects_score` se deriva de columnas realmente consumidas downstream:
homología DIAMOND, localización, conservación BV-BRC e InterPro pueden afectar
score cuando su evidencia es utilizable. Los hits de metadatos bibliográficos
se mantienen sin impacto porque no satisfacen el filtro de literatura curada.

## Coherencia de artefactos derivados

El paquete online-strict usa `ranking_nodos.csv` como fuente canonica de los
seis campos de procedencia por candidato y los propaga a
`ranking_nodos_phase3.csv` mediante `protein_id`. La etiqueta de mezcla se
calcula con una sola funcion y conserva la precedencia de evidencia negativa.

Las capas no resueltas se derivan una sola vez del provider audit, excluyendo
el seed de descubrimiento. La misma lista alimenta el review y la
interpretacion por candidato. El resumen CSV y su Markdown reciben los estados
finales persistidos por cada proveedor; una capa no resuelta no convierte por
si sola a un proveedor tecnicamente exitoso en proveedor fallido.

## Reglas y limitaciones actuales

Las reglas son conservadoras y se derivan de los manifiestos reales. Un éxito de conectividad no implica evidencia biológica. No se modifican pesos, fórmulas de scoring ni DIAMOND. Los proveedores antiguos que aún no escriben los campos nuevos se interpretan mediante los contadores y estados existentes.

## Pasos futuros sugeridos

Propagar los cinco campos directamente desde cada proveedor, validar semántica específica por capa y decidir por separado —con revisión científica— qué evidencias deben cambiar `affects_score`.
