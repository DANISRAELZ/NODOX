# User-curated end-to-end evidence flow

## Proposito

Este documento resume el flujo completo para aceptar informacion ingresada por
el usuario, validarla, importarla como capa propia y resolverla sin mezclarla
con demo, proxy, cache, `controlled_reference` ni fuentes online. El objetivo es
cerrar el circuito operativo de `user_curated` como evidencia trazable dentro de
Nodos Funcionales, manteniendo separadas la procedencia, la confianza y la
priorizacion terapeutica.

Una capa `user_curated` es evidencia preparada, aportada o revisada por el
usuario para el organismo, cepa, aislado, linaje o conjunto de cepas que se
declara en la corrida. Se trata como evidencia ingresada por el usuario porque
su origen, revision y limites quedan bajo responsabilidad documental del paquete
local: manifest, notas, archivos fuente y provenance.

`user_curated` debe mantenerse separada de otras categorias:

- `demo`: datos pequenos para probar el software, no evidencia biologica real.
- `proxy`: valores aproximados o fallback explicitos, utiles para continuidad
  tecnica pero insuficientes para conclusiones fuertes.
- `cache`: resultados reutilizados de corridas o consultas previas; ayudan a
  reproducibilidad, no son evidencia nueva del usuario.
- `controlled_reference`: snapshots o fixtures congelados para contratos y
  comparacion metodologica; no sustituyen datos reales del organismo nuevo.
- `online` o fuentes online: respuestas frescas de proveedores externos; deben
  entrar en fases separadas y por el resolvedor, no como bypass.

## Flujo end-to-end

1. Preparar archivos

   El usuario crea un paquete local, usualmente bajo
   `user_curated_staging/<project_id>/`, con `README.md`, `manifest.csv`,
   `raw_inputs/`, `notes/` y `provenance/`. Esta carpeta es local y no debe
   agregarse al repositorio si contiene datos reales o sensibles.

2. Validar el dataset

   `scripts/validate_user_curated_dataset.ps1` revisa el manifest, compara
   encabezados contra plantillas cuando se declaran, detecta columnas requeridas
   faltantes, placeholders y mezclas visibles con demo, proxy, cache, online o
   `controlled_reference`. No importa datos, no ejecuta pipeline y no calcula
   scoring.

3. Validar el manifest

   `scripts/validate_user_curated_manifest.py` y el wrapper PowerShell
   `scripts/validate_user_curated_manifest.ps1` verifican el contrato minimo del
   manifest: columnas esperadas, campos obligatorios y `source_type=user_curated`.
   Esta validacion es estructural y de procedencia/provenance minima; no acepta
   cientificamente el dataset.

4. Importar el dataset

   `import_dataset.py` normaliza un CSV compatible hacia el esquema interno. Con
   `--validate-user-curated-manifest`, se detiene si el manifest es invalido. Con
   `--as-user-layer`, escribe la capa normalizada en `workspace/data_user/` y
   conserva el export original en `workspace/data_user/source_exports/`.

5. Resolver como capa de usuario

   El resolvedor por capas lee `data_user/`, `data_cache/`, `data_external/` y
   proxies/defaults segun la estrategia configurada para cada capa
   (`user_preferred`, `external_preferred` o `merge_with_priority`). El flujo
   `user_curated` no debe cambiar prioridades globales ni saltarse
   `layer_registry.py` o `layer_resolver.py`.

6. Interpretar dentro del proyecto

   Una vez resuelta, la capa puede contribuir a reportes, auditorias y ranking
   como evidencia trazable. Su uso sigue siendo interpretativo: el sistema
   prioriza hipotesis terapeuticas, no produce validacion definitiva.

## Archivos esperados

Las columnas exactas deben tomarse de `data_templates/`. Esta lista describe el
papel de cada archivo sin crear contratos nuevos.

| Archivo o plantilla | Uso esperado |
| --- | --- |
| `gene_list_template.csv` | Inventario basico de genes o proteinas del paquete, con organismo, cepa, identificadores y fuente. |
| `functional_annotations_template.csv` | Anotaciones funcionales revisadas, producto, ruta, terminos funcionales y estado de evidencia. |
| `conservation_template.csv` | Conservacion por alcance definido, cepas, aislados o linajes, incluyendo senales como core genome o cobertura si existen. |
| `organism_profile_template.csv` | Perfil del organismo, cepa, taxonomia, fuentes disponibles, hospedero/contexto y notas del curador. |
| `evolutionary_escape_risk_template.csv` | Subcapa evolutiva con variables de tolerancia, redundancia, costo, restriccion y riesgo cuando hay evidencia disponible. |
| `manual_curation_template.csv` | Decisiones de curacion manual, resumen de evidencia, estado, referencia o nota. |
| `external_sources_template.csv` | Exports externos revisados por el usuario, con base, version, fecha, identificador y estado de evidencia. |
| `user_curated_dataset_manifest_template.csv` | Manifest operativo por dataset: organismo, cepa, version, curador, `source_type`, provenance, archivo, esquema y notas. |

Para una corrida minima que alimente el pipeline sin demo, revisar tambien las
capas obligatorias descritas en `docs/user_curated_validation_protocol.md` y las
plantillas internas de `essentiality`, `virulence`, `human_homologs` y
`localization`.

## Procedencia/provenance

La procedencia se conserva en dos niveles. Primero, el paquete local documenta
fuente, curador, version, fecha, notas, referencias y estado de evidencia en el
manifest, `notes/` y `provenance/`. Segundo, al resolver capas, el pipeline debe
propagar metadatos por capa:

- `<layer>_source_type`
- `<layer>_source_name`
- `<layer>_is_user_supplied`
- `<layer>_is_external`
- `<layer>_is_cached`
- `<layer>_is_proxy`
- `<layer>_confidence`
- `<layer>_retrieval_status`

`user_curated` significa evidencia real aportada o revisada por el usuario para
el alcance declarado. `controlled_reference` significa referencia congelada para
verificar contratos. `demo` prueba el software. `proxy` aproxima faltantes.
`cache` reutiliza resultados. `online` consulta proveedores externos. Estas
categorias pueden afectar la interpretacion y la confianza, pero no deben
confundirse con el score terapeutico.

## Interpretacion de scores

`therapeutic_priority_score` y `evidence_confidence_score` son conceptos
diferentes. `therapeutic_priority_score` ordena hipotesis terapeuticas dentro de
las reglas del modelo. `evidence_confidence_score` resume cuanta evidencia
trazable sostiene la lectura.

Un score terapeutico alto no equivale automaticamente a confianza alta. Una
confianza alta tampoco significa automaticamente prioridad terapeutica alta: un
candidato puede estar bien documentado y aun asi tener prioridad baja bajo las
reglas actuales.

Un candidato con `therapeutic_priority_score` alto y
`evidence_confidence_score` bajo debe interpretarse como hipotesis priorizada
que requiere validacion experimental, revision microbiologica y evaluacion
farmacologica antes de elevar cualquier conclusion.

Nodos Funcionales es una plataforma de priorizacion terapeutica computacional.
No es una herramienta clinica, no predice eficacia definitiva, no recomienda uso
terapeutico directo y no sustituye validacion experimental ni revision experta.

## Riesgo evolutivo

La subcapa evolutiva puede incluir o derivar senales como
`evolutionary_escape_risk`, `evolutionary_constraint`, `mutation_tolerance`,
`pathway_redundancy`, `paralog_count`, `mobile_context`, `hgt_context`,
`recombination_context` y `resistance_association`, siempre segun las plantillas
y capas ya existentes.

La ausencia o insuficiencia de evidencia no equivale a bajo riesgo. Si faltan
variables evolutivas, el resultado debe leerse como riesgo no resuelto o
evidencia insuficiente, no como seguridad biologica ni durabilidad confirmada.

La subcapa evolutiva modula la interpretacion del nodo, por ejemplo robustez,
escape o durabilidad esperada, pero no sustituye funcionalidad, selectividad
frente al hospedero, accesibilidad en el sitio de infeccion, confianza de
evidencia ni validacion experimental.

## Orientacion multiorganismo

El flujo debe funcionar para cualquier organismo bacteriano siempre que el
usuario proporcione datos compatibles con las plantillas y declare el alcance
biologico. Los organismos usados en ejemplos, pruebas o snapshots son fixtures o
casos de validacion; no son valores por defecto, no limitan el alcance del
proyecto y no deben acoplar el flujo a Corynebacterium, PAO1, H37Rv ni ningun
organismo especifico.

## Comandos practicos

Crear un paquete local de trabajo:

```powershell
.\scripts\new_user_curated_dataset.ps1 -ProjectId <project_id>
```

Validar un dataset `user_curated`:

```powershell
.\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>
```

Validar solo el manifest:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\<project_id>\manifest.csv
```

Validar el manifest con Python:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py user_curated_staging\<project_id>\manifest.csv
```

Importar una capa como capa de usuario resoluble:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --workspace <workspace_dedicado> --dataset essentiality --input user_curated_staging\<project_id>\raw_inputs\essentiality.csv --validate-user-curated-manifest user_curated_staging\<project_id>\manifest.csv --as-user-layer
```

Ejecutar la suite offline estable:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```
