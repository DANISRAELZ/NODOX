# Recuperación parcial y reintentos de InterPro

## Propósito científico

Esta corrección evita que una falla transitoria en una sola proteína invalide
toda la recuperación de dominios InterPro de una corrida grande. No cambia los
pesos terapéuticos ni convierte anotaciones computacionales en validación
experimental.

## Cambio técnico

- Cada acceso InterPro aplica reintentos acotados ante timeouts, errores de red,
  HTTP 408, 425, 429 y errores transitorios 5xx.
- Los errores no transitorios se conservan sin reintentos innecesarios.
- Una corrida con respuestas válidas y algunos accesos fallidos se registra
  como `api_real_partial`, no como fallo total.
- El manifiesto conserva `successful_accession_queries`,
  `failed_accession_queries` y las notas por accession.
- La evidencia incompleta continúa siendo neutral para el score mientras no
  exista comparación bacteriana-humana equivalente.

## Limitaciones actuales

- La recuperación online-only sigue consultando dominios bacterianos como
  metadatos y no calcula por sí sola solapamiento con el hospedero.
- La disponibilidad depende de la API externa y una respuesta parcial debe
  revisarse antes de interpretación científica.
- Los reintentos reducen fallos transitorios, pero no garantizan cobertura total.

## Paso futuro sugerido

Integrar de forma incremental el proveedor comparativo existente de InterPro
después de materializar DIAMOND, de modo que los dominios bacterianos y humanos
se comparen con procedencia explícita detrás del resolvedor actual.

