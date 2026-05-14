# Guia de ejecucion en Windows PowerShell

Esta guia ayuda a ejecutar Nodos Funcionales cuando `python` no esta disponible
en `PATH` o cuando OneDrive bloquea archivos temporales.

## Abrir PowerShell

1. Abre el menu Inicio.
2. Busca `PowerShell`.
3. Entra a la carpeta del proyecto:

```powershell
cd C:\Users\danis\OneDrive\Escritorio\nodos
```

## Seleccionar Python

Los scripts intentan, en este orden:

1. La variable `PYTHON_EXE`.
2. `python`.
3. `py`.
4. `C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Para fijar explicitamente el interprete:

```powershell
$env:PYTHON_EXE="C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
```

Tambien puedes pasarlo como parametro:

```powershell
.\scripts\run_tests.ps1 -PYTHON_EXE "C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
```

## Ejecutar pruebas

```powershell
.\scripts\run_tests.ps1
```

Este script ejecuta pruebas principales y pruebas nuevas si existen.

## Ejecutar demo

```powershell
.\scripts\run_demo.ps1
```

Equivale a:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

PAO1 se usa aqui unicamente como organismo demo reproducible. Para analisis
reales, reemplace `--organism` y `--strain` por el organismo y cepa de interes y
use datos curados, importados o fuentes externas trazables.

## Consulta online generica para C. pseudotuberculosis

```powershell
python fetch_online_data.py --organism "Corynebacterium pseudotuberculosis" --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --sources uniprot string --mode online_optional --force-refresh
```

Este ejemplo consulta informacion online general del organismo. No corresponde a una coleccion particular ni a un analisis local.

Un dry-run generico puede ejecutarse con:

```powershell
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --acquisition-mode semi_auto --workspace data_sessions\corynebacterium_pseudotuberculosis_online_demo --dry-run
```

## Limpiar temporales

Para eliminar caches Python y temporales de tests:

```powershell
.\scripts\clean_project.ps1
```

Por defecto conserva:

- `data_user`
- `data_templates`
- `docs`
- `src`
- `tests`
- `data_demo`
- `results`
- `data_processed`
- salidas de `data_sessions`

Para eliminar tambien salidas generadas:

```powershell
.\scripts\clean_project.ps1 -GeneratedOutputs
```

## OneDrive y archivos bloqueados

Si aparece `PermissionError` al escribir en `results/` o `data_sessions/`, cierra
Excel, editores, exploradores de vista previa o sincronizacion que puedan estar
usando esos archivos. Luego ejecuta:

```powershell
.\scripts\clean_project.ps1
```

Si el bloqueo esta en salidas generadas y ya no las necesitas:

```powershell
.\scripts\clean_project.ps1 -GeneratedOutputs
```

## Verificar caches restantes

```powershell
Get-ChildItem -Recurse -Force -Directory -Filter "__pycache__"
Get-ChildItem -Recurse -Force -File -Filter "*.pyc"
Get-ChildItem -Force -Directory -Filter "pytest-cache-files-*"
```

Estos comandos solo inspeccionan; no borran nada.
