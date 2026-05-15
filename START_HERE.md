# START_HERE - Nodos Funcionales

## 1. Que es Nodos Funcionales

Nodos Funcionales es un pipeline bioinformatico reproducible para priorizar
blancos terapeuticos bacterianos a partir de capas de evidencia trazables. El
sistema integra datos de esencialidad, virulencia, localizacion, homologos
humanos, contexto clinico, red funcional, conservacion, riesgo evolutivo,
literatura curada y procedencia de fuentes.

El objetivo no es declarar un blanco como validado experimentalmente. El objetivo
es ordenar candidatos de forma interpretable para revision cientifica, curacion
manual y diseno de validaciones posteriores.

## 2. Que problema resuelve

Muchos proyectos generan listas de genes, proteinas o funciones candidatas, pero
esas listas suelen mezclar evidencia fuerte, evidencia incompleta, proxies,
datos demo y faltantes. Nodos Funcionales ayuda a:

- integrar capas heterogeneas en un contrato comun;
- separar evidencia real, demo, cache, proxy y faltante;
- explicar por que un candidato sube o baja en el ranking;
- comparar estrategias bactericidas, antivirulencia, sensibilizadoras y mixtas;
- auditar si un resultado depende de datos del usuario, snapshots, fuentes
  online o defaults.

## 3. Enfoque theory-first y multi-organismo

El eje conceptual del proyecto es la Teoria de Nodos Funcionales. El software,
los conectores, las plantillas, los tests y los demos son implementaciones para
operacionalizar esa teoria.

El proyecto es multi-organismo: cualquier usuario puede iniciar un workspace con
el organismo bacteriano que desea analizar, siempre que aporte o resuelva capas
de evidencia compatibles. Ningun organismo de ejemplo define el alcance del
modelo.

PAO1 no es el organismo obligatorio ni el eje conceptual del proyecto. PAO1 se
conserva solo como demo reproducible, snapshot curado o validacion controlada.

## 4. Tipos de datos y procedencia

Use esta distincion antes de interpretar un ranking:

- Datos de usuario: archivos aportados por el usuario en `data_user/` o en el
  workspace. Son la fuente preferida cuando estan curados y documentados.
- Datos demo: archivos pequenos para verificar que el pipeline corre. Sirven
  para probar el flujo, no para inferir evidencia biologica real.
- Snapshots curados: referencias congeladas para regresion, auditoria o
  comparacion controlada. No sustituyen evidencia fresca del organismo real.
- Cache: resultados guardados de resolucion taxonomica o fuentes externas.
  Mejoran reproducibilidad, pero deben distinguirse de llamadas online frescas.
- Fuentes online: proveedores externos opcionales, como STRING o UniProt, usados
  cuando el modo de ejecucion lo permite. Deben conservar procedencia, estado de
  recuperacion y confianza.

Jerarquia interpretativa recomendada:

```text
user_supplied > curated_snapshot > real_external_online > controlled_provider > inferred_proxy > demo > missing_input
```

## 5. Corrida demo controlada PAO1

Use PAO1 solo para confirmar que el flujo reproducible funciona:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Esta corrida puede generar o actualizar archivos dentro de:

```text
data_sessions/pseudomonas_aeruginosa_pao1/
```

Interprete esta corrida como demo controlado. No use sus candidatos como
evidencia biologica real ni como prueba de que PAO1 sea el default del sistema.

## 6. Iniciar una corrida para otro organismo

Para un dry-run generico sin datos demo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Organism name" --strain "Strain name" --workspace data_sessions/my_organism_workspace --dry-run --offline-only
```

Para una corrida exploratoria con datos propios, primero coloque archivos en el
workspace o en `data_user/`, y ejecute sin `--allow-demo-data`:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_pipeline.py --organism "Organism name" --strain "Strain name" --workspace data_sessions/my_organism_workspace --mode compare --taxon-resolution-mode cache_first
```

Si faltan capas obligatorias, el pipeline debe detenerse con un mensaje claro y
generar reportes de discovery/procedencia para guiar la curacion.

## 7. Outputs principales a revisar

Despues de una corrida, revise primero:

- `results/ranking_nodos.csv`: ranking principal de candidatos.
- `results/report_phase2.md`: reporte tecnico con scores, sensibilidad y
  procedencia.
- `results/top10_scientific_audit.md`: lectura cientifica de los candidatos
  priorizados.
- `results/top10_scientific_audit.csv`: version tabular del top auditado.
- `results/phase_comparison.csv`: comparacion entre modos/fases cuando aplica.
- `results/sensitivity_analysis.csv`: sensibilidad del ranking a escenarios de
  peso.
- `results/provenance_user_summary.md`: resumen legible de procedencia.
- `results/organism_profile_validation.md`: preparacion y limitaciones del
  organismo/workspace.
- `data_processed/phase2_features.csv`: features integradas antes del scoring.
- `data_processed/scored_nodes.csv`: tabla con scores calculados.

## 8. Como interpretar el ranking terapeutico

El ranking prioriza candidatos, no valida tratamientos. Lea cada candidato junto
con:

- `therapeutic_role`: clasificacion interpretable del rol terapeutico.
- `meta_priority_score` o score principal disponible: prioridad integrada.
- variables de esencialidad, virulencia, accesibilidad, seguridad del hospedero
  y contexto de infeccion;
- variables evolutivas como `evolutionary_escape_risk`,
  `evolutionary_constraint`, `mutation_tolerance`, `pathway_redundancy`,
  `paralog_count`, `mobile_context`, `hgt_context`, `recombination_context` y
  `resistance_association`;
- columnas de procedencia y confianza;
- banderas de demo, proxy, cache, faltante o evidencia negativa.

Un candidato alto con evidencia real convergente es una hipotesis mas fuerte que
un candidato alto sostenido por demo, proxies o defaults. Un candidato con datos
faltantes no debe interpretarse como seguro ni descartado: solo esta incompleto.

## 9. Limites de interpretacion

- Un score alto no equivale a validacion experimental.
- Datos demo no son evidencia biologica.
- Cache no equivale automaticamente a evidencia fresca.
- Ausencia de evidencia no es evidencia negativa.
- Proxies ayudan a priorizar, pero deben marcarse como proxies.
- Snapshots curados son referencias congeladas, no una verdad biologica
  universal.
- El ranking depende de la calidad y completitud del workspace del organismo.

Antes de usar resultados para decisiones biologicas, revise procedencia,
confianza, limitaciones y necesidad de curacion manual.

## 10. Comandos basicos de pruebas

Suite offline recomendada:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Tests de orientacion multi-organismo:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider tests/test_multiorganism_orientation.py -q
```

Tests de plantillas genericas:

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -p no:cacheprovider tests/test_generic_organism_templates.py -q
```

## 11. Recordatorio conceptual

Nodos Funcionales no es un proyecto sobre PAO1. PAO1 es un caso tecnico util
para demo, snapshot curado y regresion controlada. El centro del proyecto es la
Teoria de Nodos Funcionales aplicada de forma reproducible, interpretable y
multi-organismo.
