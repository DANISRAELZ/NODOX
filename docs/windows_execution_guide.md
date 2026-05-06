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

## Dry-run para C. pseudotuberculosis

```powershell
.\scripts\run_cpseudo_dryrun.ps1
```

Equivale a:

```powershell
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --strain "biovar ovis" --acquisition-mode semi_auto --workspace data_sessions\cpseudo_mexico --dry-run
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
