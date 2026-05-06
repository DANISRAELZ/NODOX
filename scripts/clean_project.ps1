param(
    [switch]$GeneratedOutputs
)

$ErrorActionPreference = "Stop"

function Remove-PathSafe {
    param([string]$PathValue)
    if (Test-Path -LiteralPath $PathValue) {
        Write-Host "[OK] Removing $PathValue"
        Remove-Item -LiteralPath $PathValue -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "[OK] Cleaning Python and test caches"

Get-ChildItem -Path . -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-PathSafe -PathValue $_.FullName
}

Get-ChildItem -Path . -File -Recurse -Force -Include "*.pyc" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-PathSafe -PathValue $_.FullName
}

Remove-PathSafe -PathValue ".pip_tmp"
Remove-PathSafe -PathValue ".tmp_tests"
Remove-PathSafe -PathValue ".pytest_cache"

Get-ChildItem -Path . -Directory -Force -Filter "pytest-cache-files-*" | ForEach-Object {
    Remove-PathSafe -PathValue $_.FullName
}

Get-ChildItem -Path "src" -Directory -Force -Filter "*.egg-info" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-PathSafe -PathValue $_.FullName
}

if ($GeneratedOutputs) {
    Write-Host "[WARN] Removing generated outputs because -GeneratedOutputs was provided"
    Remove-PathSafe -PathValue "results"
    Remove-PathSafe -PathValue "data_processed"
    Get-ChildItem -Path "data_sessions" -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-PathSafe -PathValue (Join-Path $_.FullName "results")
        Remove-PathSafe -PathValue (Join-Path $_.FullName "data_processed")
    }
} else {
    Write-Host "[WARN] Generated outputs were not removed. Use -GeneratedOutputs to remove results/data_processed outputs."
}

Write-Host "[OK] Clean completed. data_user, data_templates, docs, src, tests and data_demo are preserved."
