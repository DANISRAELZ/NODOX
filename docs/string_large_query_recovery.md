# Recuperación de STRING para universos grandes

## Propósito

Esta corrección permite consultar STRING con universos bacterianos grandes sin
codificar todos los identificadores en una URL GET. No cambia el resolvedor por
capa, los pesos, los umbrales ni la interpretación de los scores.

## Problema observado

La implementación anterior enviaba hasta 1,000 identificadores en una sola URL.
La URL podía superar los límites del servidor o de intermediarios HTTP y el
fallo terminaba resumido como `provider_unavailable`, aun cuando el endpoint
mínimo de STRING sí era accesible.

## Cambio implementado

- `get_string_ids` usa POST con formulario `application/x-www-form-urlencoded`.
- `network` usa POST para conservar el conjunto completo y sus aristas cruzadas.
- Los identificadores ya no aparecen en la URL de auditoría.
- El manifiesto registra método y tamaño del cuerpo enviado.
- Si la consulta falla antes de producir una red, el manifiesto resumido conserva
  `error_detail` en vez de reducir toda causa a `provider_unavailable`.
- Los errores transitorios de transporte y los estados HTTP 408, 425, 429 y
  5xx seleccionados respetan los reintentos configurados.
- El runner estándar acepta `--string-timeout-seconds` y
  `--string-max-retries`; los overrides quedan registrados en
  `online_only_run_manifest.json` y no modifican los defaults del repositorio.
- La evidencia continúa entrando por `fetch_string_functional_network()` y el
  resolvedor existente.

## Trazabilidad

Una red solo afecta el score cuando existen mappings utilizables y aristas con
ambos extremos aceptados. El manifiesto conserva `retrieval_status`,
`mapping_success`, `usable_evidence`, `affects_score`, conteos de aristas y
procedencia. Una respuesta conectada pero vacía no se convierte en evidencia
positiva.

## Limitaciones

- STRING puede imponer límites propios al número de proteínas o al tamaño de la
  red incluso usando POST.
- La disponibilidad sigue dependiendo de red, DNS, CDN y estado del proveedor.
- La red obtenida es evidencia computacional contextual, no validación
  experimental.
- No se implementa batching de la red porque dividirla ingenuamente perdería
  interacciones entre lotes.

## Paso futuro sugerido

Si STRING rechaza universos que excedan su límite de POST, implementar una
estrategia explícita de recuperación masiva que preserve aristas cruzadas o usar
los archivos versionados de descarga de STRING detrás del resolvedor actual.

