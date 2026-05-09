# Consulta online organism-first

## Que es

La consulta online organism-first permite iniciar un workspace a partir del nombre de un organismo, sin exigir una lista local previa de genes. El flujo resuelve taxonomia, consulta fuentes online generales y escribe capas parciales con procedencia explicita.

Este flujo es multi-organismo. Corynebacterium pseudotuberculosis puede usarse como ejemplo generico de organismo ingresado por el usuario; no representa una coleccion particular de aislados ni un proyecto genomico independiente.

## Comando de ejemplo

```powershell
python fetch_online_data.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions/corynebacterium_pseudotuberculosis_online_demo --sources uniprot string --mode online_optional --force-refresh
```

Si `python` no esta en PATH, usar el ejecutable Python disponible del entorno.

## Fuentes iniciales

- Taxonomia: resolucion por catalogo/cache/API configurada.
- UniProt: genera `candidate_universe.csv`, `localization.csv` y proxies conservadores de `virulence.csv` si la anotacion lo justifica.
- STRING: genera o enriquece `functional_network.csv` usando los candidatos recuperados.

No se simulan VFDB, CARD, PHASTEST, AlienHunter, mobileOG ni DEG como fuentes reales. Si no hay conector real o archivo del usuario, esas evidencias quedan como faltantes o insuficientes.

## Capas generadas

- `data_raw/candidate_universe.csv`
- `data_raw/localization.csv`
- `data_raw/virulence.csv`
- `data_raw/functional_network.csv`
- `data_raw/evolutionary_escape_risk.csv`
- `results/online_enrichment_report.md`
- `results/online_enrichment_audit.csv`

## Interpretacion de procedencia

- `real_external_online`: respuesta online general de una fuente real.
- `inferred_proxy`: inferencia trazable desde anotaciones, con menor peso interpretativo.
- `controlled_provider`: salida deterministica del sistema, no evidencia experimental.
- `curated_snapshot`: snapshot versionado y documentado.
- `user_supplied`: dato cargado por el usuario.
- `missing_input`: no hubo fuente utilizable.
- `insufficient_evidence`: hay informacion parcial, pero no alcanza para afirmar la capa.

`missing_input` e `insufficient_evidence` no son evidencia negativa.

## Limitaciones

- UniProt puede devolver anotaciones incompletas o sin localizacion.
- STRING requiere identificadores mapeables y al menos dos candidatos.
- Sin pangenoma, SNPs, HGT, movilidad genetica o resistoma local, `evolutionary_escape_risk.csv` queda conservador: muchos campos se reportan como `unknown`.
- El ranking completo puede requerir capas obligatorias adicionales como esencialidad y homologos humanos.

## Agregar conectores futuros

Todo conector nuevo debe pasar por la arquitectura de proveedores/resolvedor existente, preservar procedencia y no presentarse como evidencia real si solo es un stub, proxy o plan futuro.
