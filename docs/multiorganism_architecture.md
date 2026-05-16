# Arquitectura Multiorganismo

## Vision general

Nodos Funcionales esta organizado como una plataforma multiorganismo. Cada analisis pertenece a un workspace independiente y puede usar datos de usuario, fuentes externas opcionales, cache reproducible, proveedores controlados, datos demo o proxies auditadas.

Esta arquitectura es una forma de operacionalizar y validar la Teoria de Nodos Funcionales en distintos organismos. El soporte multi-organismo no es un fin separado: permite probar que los postulados teoricos se expresan como capas de evidencia, procedencia, scoring y ranking explicable sin depender de un organismo concreto.

## Multiorganism design principle

La arquitectura no esta limitada a PAO1, `Corynebacterium pseudotuberculosis` ni H37Rv. Esos organismos funcionan como demo, validacion prioritaria y validacion cruzada, respectivamente. El sistema debe mantenerse generalizable a cualquier organismo bacteriano que el usuario ingrese.

Las capas de evidencia se resuelven por contratos, procedencia y configuracion por capa, no por nombres de organismos. Si una fuente externa no existe, no responde o no fue consultada, el sistema debe registrar ausencia o incompletitud de evidencia sin convertirla en evidencia biologica negativa. Los datos de usuario y los snapshots controlados deben poder cubrir temporalmente el contrato siempre que declaren confianza, limitaciones y procedencia.

## Contrato evolutivo multi-organismo

Cada workspace multi-organismo debe preservar la subcapa evolutiva como parte
vital de la Teoria de Nodos Funcionales. La arquitectura debe conservar
`evolutionary_escape_risk` y `evolutionary_constraint` como senales centrales
para interpretar robustez terapeutica y restriccion del escape.

Las variables `mutation_tolerance`, `pathway_redundancy`, `paralog_count`,
`mobile_context`, `hgt_context`, `recombination_context` y
`resistance_association` deben mantenerse como dimensiones interpretables, aun
cuando un organismo nuevo no tenga evidencia completa. La ausencia de evidencia
evolutiva no debe interpretarse como bajo riesgo de escape; debe reportarse como
evidencia faltante, insuficiente o dependiente del metodo.

Los datos demo, snapshots o proveedores controlados pueden ayudar a probar el
contrato, pero no sustituyen evidencia real del usuario ni evidencia externa
trazable para un organismo concreto.

## Flujo del sistema

```text
Usuario ingresa organismo
     ↓
Resolucion taxonomica
     ↓
Creacion o reutilizacion de workspace
     ↓
Carga de datos del usuario
     ↓
Integracion de fuentes externas opcionales
     ↓
Normalizacion de capas
     ↓
Auditoria de procedencia
     ↓
Calculo de scores
     ↓
Clasificacion de rol terapeutico
     ↓
Ranking explicable
     ↓
Reporte cientifico
```

## Workspace

La convencion actual crea workspaces en:

```text
data_sessions/<organism_slug>_<strain_slug>/
```

La estructura funcional actual es:

- `config/`
- `data_raw/`
- `data_processed/`
- `results/`

Ruta de evolucion recomendada, sin romper compatibilidad:

- `input/` como alias futuro de `data_raw/`;
- `processed/` como alias futuro de `data_processed/`;
- `results/` para salidas tabulares;
- `audit/` para auditorias especializadas;
- `reports/` para Markdown/HTML;
- `cache/` para cache por workspace;
- `manifest.json`;
- `organism_config.yaml`.

## Capas de evidencia

El sistema integra capas de esencialidad, virulencia, homologia con hospedero, localizacion, conservacion, red funcional, anotacion del hospedero, impacto clinico, contexto de enfermedad, sitio de infeccion, soporte bibliografico, redundancia, sensibilidad colateral y riesgo de escape evolutivo.

## Entradas

- Minima: organismo, cepa opcional y candidatos.
- Intermedia: candidatos mas esencialidad, virulencia, conservacion, localizacion y homologia con hospedero.
- Avanzada: pangenoma, red funcional, resistoma, viruloma, expresion, literatura curada, contexto clinico y riesgo evolutivo.

## Fuentes de datos

Las capas pueden provenir de:

- `data_user/` o archivos importados por el usuario;
- `data_cache/`;
- `data_external/`;
- proveedores externos opcionales como STRING, UniProt, DEG, VFDB, BV-BRC o InterPro;
- proveedores controlados internos;
- datos demo;
- proxies derivadas.

La integracion de proveedores reales debe pasar por el resolvedor de capas y por `fetch_layer_external_source()` o una fachada compatible. No se debe saltar la prioridad configurable por capa (`user_preferred`, `external_preferred`, `merge_with_priority`).

## Snapshots curados de referencia

Los snapshots curados son referencias congeladas para comparar ejecuciones, no fuentes online vivas. La estructura recomendada separa:

- PAO1 como demo controlado y validacion STRING/UniProt cerrada;
- `Corynebacterium pseudotuberculosis` biovar ovis como ejemplo generico con scaffold controlado offline;
- H37Rv como validacion cruzada.

Cada snapshot debe registrar organismo, cepa o alcance de cepa cuando exista, taxon id o limitacion explicita si no existe, fecha de adquisicion, modo de adquisicion, fuente STRING, fuente UniProt, estado de cache, estado de evidencia, confidence por fuente, procedencia, limitaciones y checksums cuando aplique.

## Auditoria y ranking

Cada capa resuelta propaga tipo de fuente, nombre, cache, proxy, confianza y estado de recuperacion. Los reportes separan datos de usuario, externos, curados, demo, proxy y controlados. El ranking conserva Fase 1/Fase 2 y agrega columnas progresivas de contexto terapeutico, rol terapeutico y riesgo evolutivo.

## Compatibilidad

No se eliminan `legacy_score_final`, `ranking_nodos_legacy.csv`, `ranking_nodos.csv`, `phase_comparison.csv`, Fase 1, Fase 2 ni proveedores controlados. La Fase 3 sigue siendo opcional.

## Agregar un organismo

1. Ejecutar `run_pipeline.py --organism "NOMBRE" --strain "CEPA" --workspace data_sessions/mi_workspace --dry-run`.
2. Revisar `results/discovery_report.md`.
3. Completar o importar CSVs usando `data_templates/`.
4. Activar fuentes externas opcionales si corresponde.
5. Ejecutar `run_pipeline.py --organism "NOMBRE" --strain "CEPA" --workspace data_sessions/mi_workspace --mode compare`.
6. Revisar ranking, auditorias y faltantes.

## Limitaciones actuales

- Algunas fuentes externas dependen de conectividad y cobertura del organismo.
- Los datos demo no son evidencia biologica real.
- Los proveedores controlados mantienen continuidad del pipeline, pero no sustituyen curacion experimental.
- La estructura futura `input/processed/audit/reports/cache` esta documentada como evolucion, no como migracion obligatoria.
