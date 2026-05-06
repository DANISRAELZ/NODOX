param(
    [string]$PYTHON_EXE = $env:PYTHON_EXE
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Preferred)
    $candidates = @()
    if ($Preferred) { $candidates += $Preferred }
    $candidates += @(
        "python",
        "py",
        "C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
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

$Python = Resolve-Python -Preferred $PYTHON_EXE
Write-Host "[OK] Python: $Python"
Write-Host "[OK] Running Corynebacterium pseudotuberculosis dry-run"
& $Python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --strain "biovar ovis" --acquisition-mode semi_auto --workspace "data_sessions\cpseudo_mexico" --dry-run
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Dry-run failed."
    exit $LASTEXITCODE
}
Write-Host "[OK] Dry-run completed."
