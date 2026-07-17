# Fase 7H: reparacion conservadora de conexion con proveedores externos

## Proposito cientifico

La Fase 7H corrige la forma en que el pipeline interpreta respuestas tecnicas de VFDB, DEG y BV-BRC durante ejecuciones online-only. El objetivo no es agregar evidencia nueva ni modificar la priorizacion terapeutica, sino evitar que HTML, endpoints cambiados, respuestas vacias o fallas de red se conviertan accidentalmente en evidencia biologica positiva o negativa.

## Variables y campos auditados

Los manifests de los conectores incorporan o preservan estos campos de procedencia:

- `provider_url`: URL final consultada o URL configurada si la solicitud falla.
- `http_status`: codigo HTTP cuando existe.
- `content_type`: encabezado `Content-Type` observado cuando existe.
- `payload_type`: clasificacion tecnica (`json`, `tabular_text`, `html`, `empty`, `unexpected_text`, `network_error`, `timeout`).
- `retrieval_status`: estado conservador final.
- `rejection_reason`: razon tecnica para rechazar el payload como evidencia.
- `affects_score`: siempre `false` en estas correcciones.

## Reglas de decision

### VFDB

- JSON o texto tabular solo se acepta si contiene registros estructurados verificables.
- HTML, texto inesperado, payload vacio o endpoint cambiado se degrada a `deprecated_or_changed` o `unresolved`.
- HTTP 404 se registra como `not_found`.
- No se infiere virulencia desde HTML, redirecciones, errores o respuestas no estructuradas.

### DEG

- La ruta de consulta JSON historica se trata como valida solo si devuelve JSON estructurado.
- HTML se clasifica como `html_instead_of_structured_payload`.
- Texto tabular o ZIP no se parsea desde este conector hasta tener un adaptador explicito, probado y documentado.
- No se infiere esencialidad desde HTML ni desde formato inesperado.

### BV-BRC

- JSON estructurado no vacio puede pasar al mapeo conservador existente.
- JSON/lista vacia se clasifica como `verified_empty_payload`.
- HTTP 401/403 se clasifica como `auth_or_permission_error`.
- HTTP 404 se clasifica como `not_found`.
- Errores de red o timeouts se clasifican como `unresolved`.
- Un payload vacio no se interpreta como ausencia biologica fuerte.

## Limitaciones actuales

- VFDB no tiene una ruta programatica estable verificada en la configuracion 7H; no se inventa scraping ni URL alternativa.
- DEG tiene una descarga oficial ZIP documentada, pero requiere un adaptador especifico antes de alimentar registros al pipeline.
- BV-BRC puede devolver respuestas vacias por parametros de consulta, cobertura del endpoint o limites de taxon/genoma; ese estado es tecnico, no biologico.
- Estas correcciones no cambian scoring, pesos, reglas de ranking ni interpretacion terapeutica.

## Pasos futuros sugeridos

Fase 7I deberia implementarse solo si 7H queda verde. El siguiente paso logico es agregar adaptadores de formato explicitamente versionados para fuentes con ruta estable ya verificada, empezando por DEG ZIP/CSV y BV-BRC con resolucion previa de `genome_id`, manteniendo `affects_score=false` hasta validar la integracion cientifica.
