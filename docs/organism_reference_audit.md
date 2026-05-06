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
- `data_user/cpseudotuberculosis_biovar_ovis/` es un paquete de plantillas/curacion especifico, conservado como caso de validacion biologica.

## Decision

No se eliminaron organismos concretos. Se reclasificaron como demos, casos de prueba, cache reproducible, ejemplos de documentacion o paquetes de curacion opcionales.
