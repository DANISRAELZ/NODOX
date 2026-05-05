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

## Limitaciones

Algunas pruebas online usan mocks, pero se mantienen marcadas como `online` porque validan contratos de conectores externos. Esto evita que entren por accidente en la validacion offline obligatoria.
