# Fase 7I: remediacion STRING/OpenSSL en Windows

## Problema

La suite se cortaba en Windows con `OPENSSL_Applink` durante pruebas que debian ser offline. El fallo aparecia primero en:

`tests/test_layer_external_sources.py::LayerExternalSourceTests::test_functional_network_layer_uses_string_provider`

## Causa

`string_api.py` construia el contexto SSL antes de usar el `urlopen` mockeado por la prueba. En el runtime local de Windows, crear ese contexto desde algunas rutas del entorno podia abortar el proceso antes de que pytest mostrara un traceback.

Tambien habia tests de STRING que preparaban o reejecutaban pipeline en modo online por defecto, lo que podia activar proveedores secundarios no mockeados.

## Correccion

- STRING usa ahora `request_provider_payload()` de `provider_response_audit.py`.
- El helper no construye contexto SSL cuando el opener recibido es un mock o una inyeccion de prueba.
- Los tests STRING que solo validan integracion local fijan modo offline o evitan reruns online no necesarios.
- Errores SSL se clasifican como `ssl_error` y no generan evidencia positiva ni negativa fuerte.

## Garantias

- No se modifico scoring.
- No se modificaron pesos ni ranking.
- STRING sigue siendo no bloqueante.
- La suite offline no requiere red real para estos tests.
- La evidencia funcional solo se deriva de payload JSON estructurado mockeado o real verificable.
