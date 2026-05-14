param(
    [string]$PYTHON_EXE = $env:PYTHON_EXE
)

# Demo script for organism-first online enrichment.
# This validates the multi-organism implementation of the Functional Nodes Theory.
# Corynebacterium pseudotuberculosis is used only as an example organism.

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Preferred)
    $DefaultCodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $candidates = @()
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

$Python = Resolve-Python -Preferred $PYTHON_EXE
Write-Host "[OK] Python: $Python"
Write-Host "[OK] Running Corynebacterium pseudotuberculosis dry-run"
& $Python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --acquisition-mode semi_auto --workspace "data_sessions\corynebacterium_pseudotuberculosis_online_demo" --dry-run
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Dry-run failed."
    exit $LASTEXITCODE
}
Write-Host "[OK] Dry-run completed."
