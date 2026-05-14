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
Write-Host "[OK] Running PAO1 demo pipeline"
Write-Host "[INFO] PAO1 is used only as a reproducible demo organism, not as a project default."
& $Python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Demo pipeline failed."
    exit $LASTEXITCODE
}
Write-Host "[OK] Demo pipeline completed."
