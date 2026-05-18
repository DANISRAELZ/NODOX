param(
    [string]$ProjectId = "",
    [string]$PYTHON_EXE = $env:PYTHON_EXE
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Preferred)
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $DefaultCodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $candidates = @()
    if (Test-Path $VenvPython) { $candidates += $VenvPython }
    if ($Preferred) { $candidates += $Preferred }
    $candidates += @("python", "py", $DefaultCodexPython)
    foreach ($candidate in $candidates) {
        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {
            continue
        }
    }
    throw "No se encontro un interprete Python. Define PYTHON_EXE con la ruta completa."
}

if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    Write-Host "Uso: .\scripts\new_user_curated_dataset.ps1 -ProjectId <project_id>"
    Write-Host "Crea una carpeta local ignorada en user_curated_staging\<project_id>."
    exit 2
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$Python = Resolve-Python -Preferred $PYTHON_EXE

Write-Host "[OK] Python: $Python"
Write-Host "[INFO] Creando scaffold local user_curated para: $ProjectId"
Write-Host "[INFO] No se descargan datos, no se importa nada, no se ejecuta pipeline ni scoring."

& $Python scripts\create_user_curated_staging.py $ProjectId
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo crear el scaffold. Revise el project_id o si la carpeta ya existe."
    exit $LASTEXITCODE
}

Write-Host "[NEXT] Complete user_curated_staging\$ProjectId\README.md"
Write-Host "[NEXT] Complete user_curated_staging\$ProjectId\manifest.csv"
Write-Host "[NEXT] Coloque archivos reales solo en user_curated_staging\$ProjectId\raw_inputs\"
Write-Host "[NEXT] Valide con: .\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\$ProjectId"
