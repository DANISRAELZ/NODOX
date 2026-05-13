# scripts/run_cpseudo_dryrun.ps1
# Dry-run controlado para Corynebacterium pseudotuberculosis.
# No representa validación biológica completa; sirve para verificar ejecución
# multi-organismo del pipeline en Windows.

param(
    [string]$PYTHON_EXE = "",
    [string]$Organism = "Corynebacterium pseudotuberculosis",
    [string]$Strain = "",
    [string]$Mode = "compare"
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param(
        [string]$RequestedPython = ""
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedPython)) {
        return $RequestedPython
    }

    $CandidatePython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

    if (Test-Path $CandidatePython) {
        return $CandidatePython
    }

    return "python"
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PYTHON_EXE = Resolve-Python -RequestedPython $PYTHON_EXE

Write-Host "[INFO] Project root: $ProjectRoot"
Write-Host "[INFO] Python: $PYTHON_EXE"
Write-Host "[INFO] Organism: $Organism"
Write-Host "[INFO] Strain: $Strain"
Write-Host "[INFO] Mode: $Mode"

& $PYTHON_EXE run_pipeline.py `
    --organism $Organism `
    --strain $Strain `
    --allow-demo-data `
    --mode $Mode

if ($LASTEXITCODE -ne 0) {
    throw "run_pipeline.py failed with exit code $LASTEXITCODE"
}

Write-Host "[OK] Corynebacterium pseudotuberculosis dry-run completed."