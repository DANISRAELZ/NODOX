# Estrategia de pruebas

## Proposito

Separar las pruebas permite ejecutar una validacion minima offline en Windows/OneDrive sin depender de internet ni de corridas largas del pipeline.

## Marcadores pytest

- `unit`: pruebas rapidas y deterministas de funciones, helpers o DataFrames pequenos.
- `integration`: pruebas que conectan varias etapas, leen/escriben workspaces o validan salidas del pipeline.
- `online`: pruebas que consultan o simulan conectores de APIs externas como UniProt, STRING, DEG, VFDB, BV-BRC o NCBI.
- `slow`: pruebas validas localmente pero mas costosas que la suite normal.
- `e2e`: pruebas de CLI o pipeline completo.

`tests/conftest.py` agrega un marcador operacional por defecto cuando un archivo no lo declara. La prioridad es: online por nombre de archivo, integracion por archivos de pipeline/reportes, unit para lo demas.

## Comandos recomendados

Solo unitarias:

```powershell
python -m pytest -m unit -q
```

Suite minima offline, excluyendo online, lentas y e2e:

```powershell
python -m pytest -m "not online and not slow and not e2e" -q
```

Todas excepto online:

```powershell
python -m pytest -m "not online" -q
```

Solo integracion offline:

```powershell
python -m pytest -m "integration and not online" -q
```

Solo online:

```powershell
python -m pytest -m online -q
```

Solo lentas:

```powershell
python -m pytest -m slow -q
```

## Politica offline

La suite minima no debe requerir internet. Si una prueba necesita red real o conectores externos, debe llevar `online`. Si usa cache local para simular conectores, puede ser `unit` o `integration` solo si no intenta abrir red.

## Aislamiento de workspaces

Las pruebas que ejecutan validacion, normalizacion, integracion, scoring o exportacion deben usar un workspace desechable creado por `tests.helpers.make_temp_project()`. El helper copia solamente los insumos publicos necesarios a un directorio temporal del sistema y crea directorios de salida vacios.

Una prueba no debe usar `PROJECT_ROOT` como workspace mutable. En particular:

- no debe reescribir archivos versionados bajo `data_raw/`;
- no debe actualizar `config/taxon_resolution_cache.json`;
- las pruebas explicitas de escritura o reutilizacion de cache deben operar sobre la copia temporal;
- las pruebas de descubrimiento que solo necesitan leer la cache deben usar `no_write_taxon_cache=True`.

Despues de una suite offline completa, `git status --short` debe permanecer limpio. Esta comprobacion distingue resultados de prueba reproducibles de cambios reales del repositorio.

El aislamiento tambien evita dependencias por orden de ejecucion: una prueba no puede reutilizar salidas generadas por otra para cambiar silenciosamente la procedencia o la clase de confianza esperada.

La prueba base de scoring parte de los insumos versionados y, sin CSV opcionales residuales de otras pruebas, conserva la clase de confianza `controlled` y su calidad configurada. Una fuente `curated` debe aparecer solo cuando esa evidencia forme parte explicita del workspace de la prueba.

## Limitaciones

Algunas pruebas online usan mocks, pero se mantienen marcadas como `online` porque validan contratos de conectores externos. Esto evita que entren por accidente en la validacion offline obligatoria.
