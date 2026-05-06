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

$tests = @(
    "tests/test_validation.py",
    "tests/test_integration.py",
    "tests/test_scoring.py",
    "tests/test_layer_source_audit.py",
    "tests/test_evidence_strength_audit.py",
    "tests/test_cpseudotuberculosis_templates.py"
)

foreach ($test in $tests) {
    if (Test-Path $test) {
        Write-Host "[OK] Running $test"
        & $Python -m pytest $test -q
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Test failed: $test"
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "[WARN] Skipping missing test: $test"
    }
}

Write-Host "[OK] Requested tests completed."
