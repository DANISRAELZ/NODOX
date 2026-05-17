param(
    [string]$PYTHON_EXE = $env:PYTHON_EXE
)

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

# Stable offline validation: excludes online/API tests and avoids pytest cache writes.
Write-Host "[OK] Running stable offline suite: pytest -p no:cacheprovider -m 'not online' -q"
& $Python -m pytest -p no:cacheprovider -m "not online" -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Offline test suite failed."
    exit $LASTEXITCODE
}

Write-Host "[OK] Stable offline test suite completed."
