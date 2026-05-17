param(
    [string]$ManifestPath = "",
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
    $candidates += @(
        "python",
        "py",
        $DefaultCodexPython
    )
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

if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    Write-Host "Uso: .\scripts\validate_user_curated_manifest.ps1 -ManifestPath <ruta_manifest.csv> [-PYTHON_EXE <python.exe>]"
    Write-Host "Ejemplo: .\scripts\validate_user_curated_manifest.ps1 -ManifestPath .\data_user\user_curated_dataset_manifest.csv"
    exit 2
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Resolve-Python -Preferred $PYTHON_EXE
Write-Host "[OK] Python: $Python"
Write-Host "[OK] Prevalidando manifest user_curated: $ManifestPath"
Write-Host "[INFO] Esta revision no ejecuta importacion, pipeline ni scoring."

& $Python scripts\validate_user_curated_manifest.py $ManifestPath
exit $LASTEXITCODE
