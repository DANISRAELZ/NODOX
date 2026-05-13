# Auditoria de centrado teorico

Esta auditoria revisa referencias que podian hacer parecer que Nodos Funcionales se centraba en un organismo, snapshot, importador o conector. La accion aplicada fue conservar los ejemplos tecnicos utiles, pero subordinarlos explicitamente a la Teoria de Nodos Funcionales.

| Archivo | Linea/seccion | Texto o referencia | Clasificacion | Accion recomendada | Justificacion |
| --- | --- | --- | --- | --- | --- |
| `README.md` | Introduccion | Ejemplos de PAO1 y Corynebacterium junto al quick start | Ambigua | Reescribir | Se agrego enfoque conceptual para aclarar que los ejemplos son demos y no el alcance del proyecto. |
| `docs/cpseudotuberculosis_data_integration_plan.md` | Documento completo | Plan nombrado por un organismo concreto | Incorrecta | Renombrar y reescribir | Se reemplazo por `docs/functional_nodes_theory_operationalization.md`, centrado en teoria, capas y ranking. |
| `docs/multiorganism_architecture.md` | Vision general | Arquitectura multi-organismo | Correcta | Conservar con aclaracion | La arquitectura valida la teoria en distintos organismos sin fijar un organismo central. |
| `docs/online_organism_enrichment.md` | Que es | Consulta online organism-first | Ambigua | Reescribir parcialmente | La consulta online queda descrita como fuente opcional de evidencia, no como objetivo central. |
| `docs/generic_annotation_import.md` | Proposito | Importacion generica de anotaciones | Ambigua | Reescribir parcialmente | Los importadores se presentan como entrada de datos para capas teoricas. |
| `docs/curated_snapshots.md` | Proposito y snapshots disponibles | PAO1 y Corynebacterium como snapshots | Ambigua | Reescribir parcialmente | Los snapshots quedan como fixtures reproducibles para validar contratos, no como verdad central. |
| `docs/project_boundaries.md` | Separacion de proyectos | Limites frente a proyectos externos | Correcta | Expandir | Se agrega que la separacion protege el foco en la Teoria de Nodos Funcionales. |
| `docs/source_cache_policy.md` | Politica de cache | Cache de fuentes externas | Correcta | Conservar con aclaracion | La cache apoya trazabilidad de evidencia para la teoria. |
| `docs/scoring.md` | Reglas de scoring | Scores y ranking | Correcta | Conservar con aclaracion | El scoring es la traduccion cuantitativa de los postulados teoricos. |
| `docs/data_model.md` | Modelo de datos | Capas tabulares | Correcta | Conservar con aclaracion | El modelo de datos codifica las capas computacionales de la teoria. |
| `scripts/run_corynebacterium_online_demo.ps1` | Cabecera | Demo online con organismo concreto | Correcta | Conservar con comentario | Corynebacterium queda como ejemplo tecnico para validar flujo multi-organismo. |
| `tests/test_generic_organism_templates.py` | Nombre y contratos | Plantillas genericas | Correcta | Conservar | La prueba ya no depende de un organismo concreto. |
| `tests/test_online_organism_enrichment.py` | Fixtures de organismo | Corynebacterium como caso de prueba | Correcta | Conservar | El organismo aparece como mock/demo de consulta online general. |
