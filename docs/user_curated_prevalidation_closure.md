# User-Curated Prevalidation Closure

## Proposito de la fase

La fase `user_curated prevalidation` dejo preparada una puerta de control antes
de importar datos reales de usuario o ejecutar cualquier flujo del pipeline. Su
objetivo es verificar estructura, trazabilidad minima y separacion de fuentes
para manifests `user_curated`, manteniendo fuera de esta etapa los datos demo,
proxy, cache, online y `controlled_reference`.

Esta fase no busca validar biologicamente un dataset. Solo ayuda a decidir si
un conjunto de archivos esta suficientemente descrito para avanzar a revision o
importacion.

## Elementos implementados

- `data_templates/user_curated_dataset_manifest_template.csv`: plantilla
  generica y multiorganismo para declarar organismo, cepa/aislado, dataset,
  version, curador, fecha, tipo de fuente, estado de evidencia, procedencia,
  archivo de entrada, esquema y notas.
- `docs/user_curated_validation_protocol.md`: protocolo para distinguir
  `user_curated` de `controlled_reference`, demo, proxy, cache y online.
- `docs/user_curated_template_audit.md`: auditoria documental de plantillas
  disponibles y brechas de trazabilidad.
- `docs/user_curated_validation_checklist.md`: checklist operativo previo a
  importacion.
- `src/nodos_funcionales/user_curated_validation.py`: validador puro
  `validate_user_curated_manifest(path)` que devuelve una lista de errores.
- `scripts/validate_user_curated_manifest.py`: CLI minima para ejecutar la
  prevalidacion desde consola.
- `scripts/validate_user_curated_manifest.ps1`: wrapper PowerShell opcional
  para Windows, usando el script Python existente.
- `docs/dataset_import.md` y `docs/windows_execution_guide.md`: referencias de
  uso del validador, la CLI y el wrapper.

## Pruebas agregadas

- `tests/test_user_curated_templates.py`: protege el contrato de columnas de la
  plantilla manifest y evita defaults de organismos especificos.
- `tests/test_user_curated_validation.py`: cubre manifest valido, archivo
  inexistente, columnas faltantes, `source_type` incorrecto, campos requeridos
  vacios, defaults prohibidos y codigos de salida de la CLI.
- `tests/test_windows_scripts_exist.py`: verifica la presencia del wrapper
  PowerShell y que la guia Windows lo mencione.

## Limites explicitos

Esta fase:

- no ejecuta pipeline;
- no llama a `import_dataset.py`;
- no modifica ni calcula scoring;
- no genera outputs en `results/`, `data_processed/` ni `data_sessions/`;
- no valida biologicamente el dataset;
- no confirma eficacia terapeutica, seguridad, accesibilidad real ni validez
  clinica;
- no convierte datos demo, proxy, cache, online o `controlled_reference` en
  evidencia `user_curated`;
- no decide por si sola que un dataset sea aceptado cientificamente.

Pasar la prevalidacion significa solamente que el manifest cumple un contrato
estructural minimo y que puede avanzar a revision humana o a una importacion
controlada.

## Criterios de uso

Usar esta fase cuando exista un manifest de datasets reales que el usuario
quiera revisar antes de importarlos. El manifest debe:

- usar `source_type=user_curated` solo para evidencia real aportada o revisada
  por el usuario;
- incluir `organism`, `dataset_id` e `input_file`;
- conservar la separacion entre `user_curated`, `controlled_reference`, demo,
  proxy, cache y online;
- evitar defaults de organismos de demostracion o referencia;
- apuntar a esquemas de entrada compatibles con `data_templates/`.

La CLI recomendada es:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py path\to\user_curated_dataset_manifest.csv
```

En Windows tambien puede usarse:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath path\to\user_curated_dataset_manifest.csv
```

## Siguiente paso seguro

El siguiente paso recomendado es una integracion opcional con
`import_dataset.py` mediante una bandera explicita, por ejemplo una opcion de
prevalidacion de manifest antes de copiar o normalizar archivos. Esa integracion
debe seguir siendo opt-in, no debe ejecutar scoring y debe conservar una salida
clara cuando el manifest no cumpla el contrato.

No se recomienda integrar esta prevalidacion directamente en `run_pipeline.py`
ni en Snakemake hasta probarla con un dataset real revisado por el usuario.
