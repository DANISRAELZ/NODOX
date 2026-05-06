# Builder de entradas terapeuticas curadas

## Proposito cientifico

Las colas de curacion terapeutica ayudan a revisar candidatos, pero no deben entrar al pipeline hasta que una persona complete evidencia trazable. Este builder convierte solo filas completas en CSV compatibles con la arquitectura actual.

No calcula scores nuevos. No rellena evidencia faltante. No consulta internet. Su funcion es operacional: transformar curacion manual revisada en archivos que el resolvedor ya sabe consumir.

## Entradas

El script lee, si existen:

```text
results/clinical_impact_curation_queue.csv
results/disease_context_curation_queue.csv
results/therapy_site_context_curation_queue.csv
```

Solo usa columnas `curated_*`. Las columnas `current_*` sirven como contexto para la persona que cura, pero no reemplazan evidencia manual.

## Salidas

Modo recomendado para usar datos curados en la siguiente corrida:

```text
data_user/clinical_impact.csv
data_user/curated_disease_context.csv
data_user/therapy_site_context.csv
```

Modo de catalogos externos curados:

```text
data_external/curated_catalogs/clinical_impact/<catalog_key>.csv
data_external/curated_catalogs/curated_disease_context/<catalog_key>.csv
data_external/curated_catalogs/therapy_site_context/<catalog_key>.csv
```

La resolucion por capa mantiene prioridad para `data_user/`. Los catalogos externos quedan listos como artefactos reproducibles; las capas conectadas a catalogos los pueden materializar antes del proveedor controlado.

## Reglas de inclusion

Una fila de `clinical_impact` se escribe solo si tiene:

- `curated_host_direct_damage_score`
- `curated_virulence_associated_severity_score`
- `curated_clinical_impact_score`
- `curated_clinical_impact_evidence_type`
- `curated_clinical_impact_evidence_reference`

Una fila de `curated_disease_context` se escribe solo si tiene:

- `curated_infection_context_score`
- `curated_disease_context`
- `curated_infection_stage`
- `curated_context_evidence_type`
- `curated_context_evidence_reference`

Una fila de `therapy_site_context` se escribe solo si tiene:

- `curated_infection_site_access`
- `curated_infection_site`
- `curated_access_evidence_type`
- `curated_access_evidence_reference`

Los scores deben estar en rango `0.0` a `1.0`.

## Uso

Crear archivos en `data_user/`:

```powershell
& 'C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build_curated_therapeutic_inputs.py --workspace data_sessions\pseudomonas_aeruginosa_pao1 --target data_user
```

Crear catalogos externos:

```powershell
& 'C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build_curated_therapeutic_inputs.py --workspace data_sessions\pseudomonas_aeruginosa_pao1 --target external_catalog --catalog-key taxon_287
```

Para reemplazar archivos existentes:

```powershell
& 'C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build_curated_therapeutic_inputs.py --workspace data_sessions\pseudomonas_aeruginosa_pao1 --target data_user --overwrite
```

## Limitaciones actuales

- El builder no valida biologicamente una referencia; solo exige que exista un identificador trazable.
- No fusiona con archivos existentes; reemplaza solo con `--overwrite`.
- No cambia el ranking hasta que el pipeline se ejecute de nuevo y el resolvedor use los CSV generados.
- El catalogo externo de `curated_disease_context` queda preparado como artefacto; si se quiere resolverlo automaticamente como fuente externa, esa conexion debe hacerse en una iteracion separada.

## Paso futuro sugerido

Conectar tambien `curated_disease_context` a catalogos externos por organismo/enfermedad, igual que ya se hizo para `clinical_impact` y `therapy_site_context`.
