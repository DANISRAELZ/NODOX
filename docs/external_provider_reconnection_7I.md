# Fase 7I: reconexion conservadora de proveedores externos

## Proposito

La Fase 7I revisa VFDB, DEG, BV-BRC y STRING sin cambiar scoring, ranking, pesos, GUI ni interpretacion biologica. La fase intenta reconectar solo cuando hay payload estructurado verificable y mantiene degradacion conservadora cuando el proveedor devuelve HTML, ZIP sin adaptador, texto libre, errores SSL/red o payload vacio.

## Diagnostico por proveedor

### VFDB

- Endpoint configurado: `http://www.mgc.ac.cn/VFs/Down/VFs.tsv.gz`.
- Metodo: `GET`.
- Formato aceptado por el conector: JSON o texto tabular verificable con registros.
- Estado 7I: sigue degradado si el endpoint devuelve HTML, 404, texto libre o payload inesperado.
- Parser: `vfdb_api._as_records`.
- Regla conservadora: no se infiere virulencia desde HTML, texto libre, 404 o payload inesperado.

### DEG

- Endpoint configurado historico: `https://tubic.org/deg/public/index.php?query=<taxon_or_name>&format=json`.
- Descarga oficial documentada: `https://tubic.org/deg/public/download/deg_annotation_p.csv.zip`.
- Formato aceptado por el conector actual: JSON estructurado verificable.
- Estado 7I: HTML queda `html_instead_of_structured_payload`; ZIP queda `unsupported_structured_archive` hasta tener adaptador formal.
- Parser: `deg_api._as_records`.
- Regla conservadora: no se infiere esencialidad desde HTML, ZIP sin adaptador, texto libre o payload inesperado.

### BV-BRC

- Endpoint configurado: `https://www.bv-brc.org/api/genome_feature/`.
- Metodo: `GET`.
- Formato aceptado: JSON estructurado.
- Estado 7I: JSON no vacio puede conectarse como payload estructurado; JSON/lista vacia queda `verified_empty_payload`; 401/403 queda `auth_or_permission_error`; 404 queda `not_found`.
- Parser: `bvbrc_api._as_records`.
- Regla conservadora: payload vacio no se interpreta como ausencia biologica fuerte.

### STRING

- Endpoint configurado: `https://string-db.org/api`.
- Metodo: `GET`, dos pasos: `json/get_string_ids` y `json/network`.
- Formato aceptado: lista JSON estructurada.
- Estado 7I: el test de Windows que fallaba por `OPENSSL_Applink` queda offline-safe porque STRING usa el helper auditado y los tests no construyen contexto SSL cuando `urlopen` esta mockeado.
- Parser: `string_json_list_parser`.
- Regla conservadora: errores SSL/red o payload invalido no generan evidencia funcional y no bloquean ranking parcial.

## Estados conservadores

- `connected_structured_payload`: se recibio payload estructurado verificable.
- `deprecated_or_changed`: endpoint o formato ya no coincide con el contrato esperado.
- `html_instead_of_structured_payload`: proveedor devolvio HTML.
- `unsupported_structured_archive`: proveedor devolvio ZIP u otro archivo estructurado sin adaptador formal probado.
- `verified_empty_payload`: respuesta estructurada vacia.
- `auth_or_permission_error`: 401/403.
- `not_found`: 404 u organismo/consulta no encontrada.
- `network_error`, `ssl_error`, `unresolved`, `invalid_payload`: falla tecnica no interpretable biologicamente.

## Limitaciones

No se agregaron nuevas capas funcionales ni evidencia `user_curated`. DEG ZIP no se parsea todavia. VFDB no usa scraping HTML ni URLs inventadas. BV-BRC no convierte ausencia de filas en evidencia negativa. STRING no queda bloqueante.

## Siguiente paso

Fase 7J deberia formalizar contratos publicables por proveedor: campos minimos, payload fixtures versionados, matriz online-only por organismo y reglas de aceptacion antes de permitir que una fuente cambie interpretacion cientifica.
