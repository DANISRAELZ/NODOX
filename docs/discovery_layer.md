# Discovery Layer

## Propósito

La capa discovery permite iniciar el proyecto desde un microorganismo en lugar de
partir conceptualmente de CSVs manuales.

## Entrada principal

- `organism_name`
- `strain` opcional
- `strategy` opcional
- `acquisition_mode`
- `workspace` opcional

## Responsabilidades

- resolver taxonomía local mínima
- generar `organism_profile.json`
- generar `acquisition_manifest.json`
- generar `discovery_report.md`
- crear un workspace reproducible por organismo
- decidir si el motor actual puede correr ya

## Punto de inserción

Discovery ocurre antes de `scripts/01_load_and_validate.py`.

No reemplaza el motor actual; lo alimenta.

## Resolución taxonómica

Hoy usa un catálogo local configurable en `config/taxon_aliases.json`.

Estados de resolución típicos:

- `exact_local_match`
- `alias_local_match`
- `unresolved_local`

Si no hay coincidencia, el nombre ingresado se conserva como canónico provisional y
queda explícito que no se consultaron APIs externas.
