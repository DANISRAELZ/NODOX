# START HERE - Nodos Funcionales

## Que es el proyecto

Nodos Funcionales es un pipeline reproducible para priorizar nodos bacterianos con posible interes terapeutico. Integra capas como esencialidad, virulencia, localizacion, homologos humanos, conservacion, contexto clinico, riesgo de escape evolutivo y literatura curada.

El ranking ayuda a ordenar candidatos para revision cientifica. No valida experimentalmente un blanco y no convierte datos demo en evidencia biologica real.

## Fases

- Fase 1: ranking basico con esencialidad, virulencia, homologia humana y accesibilidad.
- Fase 2: agrega contexto terapeutico, prioridades interpretables y auditoria de procedencia.
- Fase 3: agrega teoria de nodos funcionales, riesgo evolutivo, calidad de evidencia, literatura curada y un ranking real separado de registros demo/template.

## Instalar dependencias

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
```

Si `python` no esta en PATH, use el Python de su entorno local o el runtime configurado para el proyecto.

## Correr demo

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode phase3 --taxon-resolution-mode offline_only
```

El demo sirve para verificar que el pipeline funciona. Cualquier fila marcada como `demo_data`, `default_value` o `template_record` no debe interpretarse como evidencia biologica real.

Para correr el modo minimo de compatibilidad Fase 1/Fase 2:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --taxon-resolution-mode offline_only
```

## Correr un organismo nuevo

```powershell
python run_pipeline.py --organism "Nombre bacteriano" --strain "Cepa" --workspace data_sessions/mi_organismo --mode phase3 --taxon-resolution-mode cache_first
```

Para evitar problemas de sincronizacion en Windows, use un workspace local estable. Si OneDrive bloquea archivos, pruebe una carpeta fuera de OneDrive.

## Perfil minimo por organismo

Antes de interpretar un ranking real, documente como minimo:

- `organism`: nombre cientifico.
- `strain`: cepa o aislado.
- `taxon_id`: identificador taxonomico, o modo de resolucion taxonomica documentado.
- Lista de genes/proteinas/nodos: al menos `protein_id` y, si existe, `gene`.
- Evidencia funcional minima: esencialidad, virulencia o anotacion funcional trazable.
- Datos de conservacion si existen.
- Fuente de anotacion: base de datos, archivo de usuario, version o fecha.

El pipeline permite analisis exploratorio con datos parciales, pero marcara baja confianza cuando falten capas criticas.

## Archivos minimos que debe llenar el usuario

Para una corrida interpretable, complete al menos:

- `data_user/essentiality.csv`
- `data_user/virulence.csv`
- `data_user/human_homologs.csv` o `data_user/human_homologs_orthology.csv`
- `data_user/localization.csv`

Para fortalecer Fase 3, agregue:

- `data_user/literature_support.csv`
- `data_user/evolutionary_escape.csv`
- `data_user/redundancy.csv`
- `data_user/contextual_essentiality.csv`
- `data_user/clinical_impact.csv`
- `data_user/therapy_site_context.csv`

## Sustituir demo por datos reales

1. Copie una plantilla desde `data_templates/` hacia `data_user/` o al workspace del organismo.
2. Rellene valores reales y referencias en las columnas de evidencia.
3. Mantenga columnas de procedencia como `database`, `source`, `reference`, `doi_or_url` o equivalentes cuando existan.
4. Ejecute sin `--allow-demo-data` si desea comprobar que no depende de ejemplos.
5. Revise `results/provenance_user_summary.md` y `results/organism_profile_validation.md` antes de interpretar candidatos.

## Tipos de evidencia

- `user_curated`: datos curados por el usuario.
- `external_real`: datos de una base externa real.
- `literature_curated`: literatura con DOI, PubMed ID, cita o referencia curada.
- `computed_from_real_data`: calculo interno derivado de datos reales.
- `controlled_provider`: proveedor controlado o stub reproducible.
- `proxy_inference`: inferencia indirecta; orienta, pero no valida.
- `default_value`: valor por defecto para mantener la ejecucion.
- `demo_data`: dato de demostracion o plantilla.
- `missing`: dato ausente; reduce confianza, pero no es evidencia negativa.

## Como interpretar el ranking

Revise primero:

- `results/ranking_nodos.csv`: ranking principal de la corrida actual. En `compare` representa Fase 2; en `legacy` copia el ranking legacy como salida primaria.
- `results/report_phase2.md`: reporte tecnico con tablas, sensibilidad, procedencia y auditorias.
- `results/candidate_explanations_simple.md`: explicacion para usuarios no tecnicos.
- `results/ranking_nodos_phase3_real_candidates.csv`: candidatos incluidos en el ranking terapeutico real o exploratorio.
- `results/ranking_nodos_phase3.csv`: todos los registros, incluidos demo/template, con banderas de exclusion.
- `results/template_or_demo_records.csv`: registros excluidos por demo/template.
- `results/top10_scientific_audit.md`: explicacion cientifica de los candidatos priorizados o del motivo por el que no hay candidatos reales.
- `results/provenance_user_summary.md`: procedencia de las capas en lenguaje no tecnico.
- `results/organism_profile_validation.md`: preparacion del organismo para demo, exploracion o analisis mas robusto.

`included_real_candidate` indica varias capas reales convergentes. `included_exploratory_with_demo_support` indica evidencia real parcial mezclada con demo/proxy/default; puede revisarse, pero requiere curacion adicional.

## Por que mi ranking real esta vacio?

Un ranking real vacio no siempre significa que no haya blancos utiles. Puede ocurrir porque:

- Todos los registros son `template_record` o `demo_record`.
- No hay ninguna capa con evidencia real por candidato.
- Las capas minimas estan ausentes o solo tienen valores por defecto.
- Las reglas de inclusion son demasiado estrictas para el estado actual de curacion.
- Existe evidencia negativa real critica de seguridad.

Para diagnosticarlo:

- Abra `results/ranking_nodos_phase3.csv` y revise `candidate_record_type`, `ranking_inclusion_status` y `ranking_inclusion_reason`.
- Abra `results/layer_evidence_summary.csv` y revise `phase3_real_evidence_layer_count`.
- Abra `results/organism_profile_validation.md` para ver que capas faltan.
- Abra `results/template_or_demo_records.csv` para confirmar si el problema son plantillas.

Si aparece `missing`, falta evidencia. Si aparece evidencia negativa real, hay una fuente trazable que justifica penalizacion o exclusion. `missing` no es lo mismo que evidencia negativa.

## Como correr pruebas

```powershell
python -m pytest -m unit -q
python -m pytest -m "not slow and not online and not e2e" -q
python -m pytest -m "unit or integration" -q
python -m pytest -m integration -q
python -m pytest -m online -q
python -m pytest -m e2e -q
```

La suite recomendada para desarrollo local es:

```powershell
python -m pytest -m "not slow and not online and not e2e" -q
```

Las pruebas `online` requieren internet o APIs externas. Las pruebas `slow` y `e2e` pueden crear workspaces completos o ejecutar el pipeline.

## Empaquetado limpio

Antes de comprimir o subir a GitHub, revise archivos generados:

```powershell
python scripts/clean_generated.py --dry-run
python scripts/clean_generated.py --apply
```

El script no debe borrar `data_templates/`, `config/`, `tests/fixtures/`, datos fuente ni documentacion. Los generados que conviene excluir incluyen `__pycache__`, `.pytest_cache`, `data_processed`, `results`, `data_sessions/*/results` y `logs`.

## Problemas frecuentes en Windows/OneDrive

- Si un CSV esta abierto en Excel, cierre Excel y vuelva a ejecutar.
- Si OneDrive muestra archivos como "solo nube", haga clic derecho y seleccione "Mantener siempre en este dispositivo".
- Si no puede escribir en `results/`, pruebe un workspace fuera de OneDrive.
- Si una ruta no existe, espere a que termine la sincronizacion o revise si OneDrive cambio el nombre de la carpeta.

## Que hacer despues

Use el demo solo para verificar ejecucion. Para un organismo real, llene las capas en `data_user/`, revise `provenance_user_summary.md`, y no interprete candidatos exploratorios como candidatos validados hasta agregar evidencia curada suficiente.
