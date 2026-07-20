# User-Curated Operational Flow

## Propósito

Este documento describe el flujo para preparar, revisar, prevalidar e importar datos `user_curated` sin ejecutar scoring ni pipeline.

Antes de trabajar con datos reales, revise:

- `docs/user_friendly_onboarding.md`
- `docs/user_curated_real_dataset_readiness.md`
- `docs/first_user_curated_dataset_startup.md`

Los datos reales deben permanecer en una carpeta local ignorada por Git.

## Punto de partida

Abra una terminal en la raíz del repositorio. No use una ruta absoluta específica de un equipo.

```powershell
cd <ruta-al-repositorio-NODOX>
```

Durante esta fase:

- no ejecute `run_pipeline.py`;
- no ejecute scoring;
- no escriba resultados científicos;
- no use datos demo como sustituto de evidencia real;
- no versiona archivos privados o sensibles.

## 1. Crear staging local

Puede crear una estructura vacía mediante:

```powershell
python scripts/create_user_curated_staging.py my_dataset
```

La carpeta queda bajo `user_curated_staging/`, ignorada por Git.

## 2. Preparar el manifest

Copie la plantilla:

```powershell
Copy-Item ./data_templates/user_curated_dataset_manifest_template.csv ./path/to/user_data/user_curated_dataset_manifest.csv
```

Columnas esperadas:

```text
organism,strain,dataset_id,dataset_version,curator_name,curation_date,source_type,evidence_status,evidence_kind,provenance,input_file,input_schema,required_for_scoring,notes
```

Campos mínimos:

- `organism`
- `dataset_id`
- `source_type=user_curated`
- `input_file`

También deben documentarse alcance, versión, responsable de revisión, fecha, estado, tipo de evidencia, procedencia, esquema, necesidad para scoring y limitaciones.

## 3. Separar procedencias

| Categoría | Uso permitido |
| --- | --- |
| `user_curated` | Evidencia real aportada o revisada para el organismo declarado. |
| `controlled_reference` | Referencia congelada para pruebas o comparación. |
| demo | Datos pequeños para demostrar el software. |
| proxy | Aproximación explícita que reduce confianza. |
| cache | Respuesta reutilizada de una ejecución previa. |
| online | Respuesta fresca de un proveedor externo. |

Estas categorías no son intercambiables.

## 4. Revisión manual

Antes de prevalidar confirme:

- existencia de cada archivo;
- correspondencia con el organismo y alcance declarados;
- identificadores no vacíos ni marcadores de plantilla;
- procedencia clara;
- faltantes e inferencias documentados;
- ausencia de datos personales o restringidos no autorizados.

## 5. Prevalidar

CLI Python:

```powershell
python scripts/validate_user_curated_manifest.py ./path/to/user_data/user_curated_dataset_manifest.csv
```

Wrapper PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/validate_user_curated_manifest.ps1 ./path/to/user_data/user_curated_dataset_manifest.csv
```

La prevalidación comprueba estructura y procedencia mínima. No confirma validez biológica.

## 6. Corregir antes de importar

Detenga el flujo ante:

- columnas incorrectas;
- `source_type` distinto de `user_curated`;
- campos mínimos vacíos;
- residuos de organismos demo;
- archivos inexistentes;
- procedencia incierta.

## 7. Importar con validación explícita

```powershell
python import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace data_sessions/user_curated_workspace --dataset essentiality --input ./path/to/user_data/essentiality.csv --validate-user-curated-manifest ./path/to/user_data/user_curated_dataset_manifest.csv
```

La bandera de validación hace que la importación se detenga cuando el manifest contiene errores.

## 8. Revisión posterior

Después de importar:

- inspeccione los archivos copiados y normalizados;
- confirme identificadores y procedencia;
- verifique que ninguna capa demo haya reemplazado datos reales;
- deténgase antes de scoring hasta obtener autorización explícita.

## Interpretación

`user_curated` indica procedencia y revisión, no validación clínica automática. Una prioridad modelada puede coexistir con confianza baja. La evidencia insuficiente debe permanecer visible como incertidumbre.
