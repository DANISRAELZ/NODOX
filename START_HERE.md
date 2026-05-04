# START HERE

## Correr demo

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode phase3 --taxon-resolution-mode offline_only
```

Si `python` no esta en PATH, use el Python de su entorno local o el runtime
configurado por Codex.

## Correr un organismo nuevo

```powershell
python run_pipeline.py --organism "Nombre bacteriano" --strain "Cepa" --workspace data_sessions/mi_organismo --mode phase3 --taxon-resolution-mode cache_first
```

## Archivos minimos

Para una corrida interpretable, complete al menos:

- `essentiality.csv`
- `virulence.csv`
- `human_homologs.csv` o `human_homologs_orthology.csv`
- `localization.csv`

Para mejorar Fase 3, agregue:

- `literature_support.csv`
- `evolutionary_escape.csv`
- `redundancy.csv`
- `contextual_essentiality.csv`

## Ejemplos reales curados

La distribucion incluye una semilla curada offline para PAO1 en
`data_external/curated_catalogs/literature_support/pseudomonas_aeruginosa_pao1.csv`.
El resolvedor la carga mediante `curated_online_examples` y la materializa en
el workspace como evidencia bibliografica real con DOI/PubMed. Use ese archivo
como ejemplo de formato y como punto de partida; para otros organismos, cree un
catalogo equivalente o complete `data_user/literature_support.csv`.

Tambien existen semillas parciales para `essentiality`, `virulence` y
`localization`. Esas filas reducen el uso de demo en PAO1, pero no sustituyen
una curacion completa: los candidatos sin fila curada siguen apareciendo como
`demo_data` o `missing` en la auditoria.

## Como interpretar confianza

- `strongly_supported_candidate`: evidencia real convergente.
- `moderately_supported_candidate`: evidencia real parcial suficiente.
- `weakly_supported_candidate`: senal util, pero incompleta.
- `exploratory_candidate`: requiere curacion adicional.
- `insufficient_evidence`: no hay datos reales suficientes.
- `deprioritized_due_to_negative_evidence`: evidencia real sugiere riesgo.

Si aparece `insufficient_evidence`, no significa que el blanco sea malo:
significa que faltan capas reales o curadas para interpretarlo.
# START HERE - Nodos Funcionales

## Que es este proyecto

Nodos Funcionales es un pipeline reproducible para priorizar nodos bacterianos con posible interes terapeutico. Integra capas como esencialidad, virulencia, localizacion, homologos humanos, conservacion, contexto clinico, riesgo de escape evolutivo y literatura curada.

## Que problema resuelve

Ayuda a ordenar candidatos para revision cientifica. No valida experimentalmente un blanco y no debe convertir datos demo en evidencia biologica real.

## Fases

- Fase 1: ranking basico con esencialidad, virulencia, homologia humana y accesibilidad.
- Fase 2: agrega contexto terapeutico, prioridades interpretables y auditoria de procedencia.
- Fase 3: agrega teoria de nodos funcionales, riesgo evolutivo, calidad de evidencia y ranking real separado de registros demo/template.

## Instalar dependencias

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
```

Si `python` no esta en PATH en Windows, usa el lanzador disponible o instala Python desde python.org.

## Correr demo

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode phase3 --taxon-resolution-mode offline_only
```

Los datos demo sirven para verificar que el pipeline funciona. No son evidencia biologica real.

## Correr un organismo nuevo

```powershell
python run_pipeline.py --organism "Nombre del organismo" --strain "Cepa" --workspace data_sessions/mi_organismo --mode phase3 --taxon-resolution-mode offline_only
```

Si no hay datos suficientes, el pipeline crea plantillas y reporta que faltan capas.

## Archivos minimos que debe llenar el usuario

- `data_user/essentiality.csv`
- `data_user/virulence.csv`
- `data_user/localization.csv`
- `data_user/human_homologs.csv`
- Recomendados para Fase 3: `strain_conservation.csv`, `functional_network.csv`, `evolutionary_escape_risk.csv`, `literature_support.csv`, `clinical_impact.csv`, `curated_disease_context.csv`, `therapy_site_context.csv`.

## Como interpretar el ranking

- `ranking_nodos.csv`: ranking principal compatible.
- `ranking_nodos_phase3.csv`: todos los registros de Fase 3, incluidos demo/template marcados.
- `ranking_nodos_phase3_real_candidates.csv`: solo candidatos terapeuticos reales.
- `template_or_demo_records.csv`: registros excluidos del ranking real.

Un score alto con baja confianza sigue siendo exploratorio.

## Como saber si el ranking es confiable

Revisa:

- `results/provenance_user_summary.md`
- `results/organism_profile_validation.md`
- `results/layer_evidence_summary.csv`
- `results/top10_scientific_audit.md`

## Tipos de evidencia

- `user_curated`: datos curados por el usuario.
- `external_real`: bases externas reales.
- `literature_curated`: literatura con DOI, PubMed o cita curada.
- `computed_from_real_data`: calculos internos desde datos reales.
- `controlled_provider`: proveedor controlado o stub reproducible.
- `proxy_inference`: inferencia proxy de baja confianza.
- `default_value`: valor por defecto para mantener ejecucion.
- `demo_data`: ejemplo o plantilla; no es evidencia biologica.
- `missing`: dato ausente.

## insufficient_evidence y unknown

`insufficient_evidence` significa que faltan datos reales suficientes. `unknown` significa que el riesgo o soporte no esta evaluado. Ninguno equivale automaticamente a evidencia negativa.

## Como correr pruebas

```powershell
python -m pytest -m unit -q
python -m pytest -m "not slow and not online" -q
python -m pytest -m integration -q
python -m pytest -m "online" -q
python -m pytest -m "e2e" -q
```

Las pruebas `online` pueden requerir internet o APIs externas. Las pruebas `slow` se excluyen de la suite rapida.

## Limpiar archivos generados

```powershell
python scripts/clean_generated.py --dry-run
python scripts/clean_generated.py --apply
```

El script no borra `data_templates/`, `config/`, `tests/fixtures/`, `data_raw/`, `data_user/` ni documentacion.

## Problemas frecuentes en Windows/OneDrive

- Si un CSV esta abierto en Excel, puede aparecer `PermissionError`. Cierra Excel y vuelve a ejecutar.
- Si OneDrive no descargo una carpeta, marca la carpeta como `Mantener siempre en este dispositivo`.
- Si no se puede escribir en `results/`, usa un workspace fuera de OneDrive o revisa permisos.
- Las rutas con espacios funcionan, pero es mejor envolverlas entre comillas.
