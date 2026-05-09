# Auditoria de Referencias a Organismos

## Resumen

Se revisaron referencias a `Corynebacterium pseudotuberculosis`, `Pseudomonas aeruginosa`, `Mycobacterium tuberculosis`, `Helicobacter pylori`, cepas como `PAO1` y `H37Rv`, y slugs como `cpseudo`/`cpseudotuberculosis`.

## A. Ejemplos validos

- Comandos del README con PAO1, H37Rv y `Corynebacterium pseudotuberculosis biovar ovis`.
- Guias de ejecucion en Windows y documentos de workflow.
- Scripts de conveniencia como `scripts/run_demo.ps1` y `scripts/run_cpseudo_dryrun.ps1`.
- Workspaces bajo `data_sessions/` usados como ejemplos reproducibles.

Estos elementos se conservan como ejemplos de uso y no como restricciones del motor.

## B. Acoplamientos problemáticos corregidos o mitigados

- La introduccion del README podia leerse como pipeline generico pero no declaraba con suficiente fuerza el alcance multiorganismo. Se actualizo con una definicion oficial.
- La guia `organism_workflow.md` no explicitaba la ruta de evolucion de workspace multiorganismo. Se agrego.
- `dataset_import.md` usaba un ejemplo con `cpseudo_demo` sin aclarar que era ilustrativo. Se actualizo.
- Los reportes principales no mostraban siempre organismo, cepa, workspace y nivel global de respaldo. Se agrego metadata multiorganismo en reportes.

## C. Casos de validacion

- Tests de resolucion taxonomica y proveedores externos usan PAO1, H37Rv, Helicobacter y Corynebacterium para cubrir cache, API, alias y fallbacks.
- `config/taxon_resolution_cache.json`, `config/taxon_aliases.json` y `config/demo_organisms.json` contienen ejemplos/cache reproducible. No son defaults obligatorios.
- `data_templates/` es el contrato generico de plantillas para cualquier organismo; los datos especificos deben cargarse en un workspace del usuario.

## Decision

No se eliminaron organismos concretos. Se reclasificaron como demos, casos de prueba, cache reproducible, ejemplos de documentacion o paquetes de curacion opcionales.

## Referencias para snapshots curados

Para la fase de consolidacion de fuentes online y snapshots, las referencias se clasifican asi:

| Organismo | Cepa | Uso esperado | Advertencia |
| --- | --- | --- | --- |
| `Pseudomonas aeruginosa` | PAO1 | Organismo demo controlado y referencia de validacion STRING/UniProt ya cerrada. | No confundir el snapshot demo con evidencia real nueva. |
| `Corynebacterium pseudotuberculosis` | biovar ovis | Organismo real prioritario del proyecto con scaffold controlado inicial. | El snapshot actual es offline/controlado; STRING y UniProt siguen sin consultarse para este organismo. |
| `Mycobacterium tuberculosis` | H37Rv | Organismo real para validacion cruzada por cobertura publica estable. | Registrar si cada fuente resuelve a cepa H37Rv o a nivel especie. |

Estas referencias no imponen defaults globales al motor. Solo orientan la preparacion de snapshots reproducibles y auditables.

## Principio multiorganismo

El proyecto no es especifico de PAO1, `Corynebacterium pseudotuberculosis` ni H37Rv. Esos nombres aparecen porque permiten cubrir modos distintos de validacion: demo controlado, organismo real prioritario y validacion cruzada. Cualquier documento, snapshot o prueba nueva debe evitar presentar esos organismos como limites del pipeline.

Cuando un organismo nuevo no tenga `taxon_id`, cepa, fuentes externas completas o cache disponible, el contrato debe permitir una entrada parcial con limitaciones explicitas y procedencia clara. Esa incompletitud no debe confundirse con evidencia biologica negativa.
