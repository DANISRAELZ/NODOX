param(
    [string]$PYTHON_EXE = $env:PYTHON_EXE,
    [switch]$RunDiscoveryDryRun
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    param([string]$Preferred)
    $DefaultCodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $candidates = @()
    if ($Preferred) { $candidates += $Preferred }
    $candidates += @(
        ".\.venv\Scripts\python.exe",
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
    throw "No Python interpreter was found. Set PYTHON_EXE to the full path."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$InputDir = Join-Path $ScriptDir "input"
$OutputDir = Join-Path $ScriptDir "output"
$WorkspaceDir = Join-Path $OutputDir "workspace"
$DataUserDir = Join-Path $WorkspaceDir "data_user"
$SourcePackageDir = Join-Path $WorkspaceDir "source_package"

$RequiredInputs = @(
    "gene_list.csv",
    "manual_curation.csv",
    "evidence_quality.csv",
    "manifest.yaml",
    "provenance.yaml",
    "notes.md"
)

foreach ($name in $RequiredInputs) {
    $path = Join-Path $InputDir $name
    if (-not (Test-Path $path)) {
        throw "Missing required demo input: $path"
    }
}

New-Item -ItemType Directory -Force -Path $DataUserDir, $SourcePackageDir | Out-Null

Copy-Item -Force -LiteralPath (Join-Path $InputDir "gene_list.csv") -Destination (Join-Path $DataUserDir "gene_list.csv")
Copy-Item -Force -LiteralPath (Join-Path $InputDir "manual_curation.csv") -Destination (Join-Path $DataUserDir "manual_curation.csv")
Copy-Item -Force -LiteralPath (Join-Path $InputDir "evidence_quality.csv") -Destination (Join-Path $DataUserDir "evidence_quality.csv")
Copy-Item -Force -LiteralPath (Join-Path $InputDir "manifest.yaml") -Destination (Join-Path $SourcePackageDir "manifest.yaml")
Copy-Item -Force -LiteralPath (Join-Path $InputDir "provenance.yaml") -Destination (Join-Path $SourcePackageDir "provenance.yaml")
Copy-Item -Force -LiteralPath (Join-Path $InputDir "notes.md") -Destination (Join-Path $SourcePackageDir "notes.md")

$RunNote = @"
# Pseudomonas aeruginosa publication demo run

Prepared workspace: $WorkspaceDir
Input provenance: user_curated
Scope: reproducible publication demo structure only
Clinical validation: no
Experimental validation: no
Clinical efficacy prediction: no

The prepared workspace contains the currently available user-curated layers.
Additional reviewed organism-specific layers are required before interpreting a
full therapeutic ranking.
"@

Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir "DEMO_RUN_NOTES.md") -Value $RunNote

Write-Host "[OK] Prepared demo workspace: $WorkspaceDir"
Write-Host "[OK] Copied user_curated inputs into data_user/"
Write-Host "[OK] Preserved manifest, provenance, and notes in source_package/"

if ($RunDiscoveryDryRun) {
    $Python = Resolve-Python -Preferred $PYTHON_EXE
    $RunPipeline = Join-Path $ProjectRoot "run_pipeline.py"
    if (-not (Test-Path $RunPipeline)) {
        throw "Missing pipeline entry point: $RunPipeline"
    }
    Write-Host "[OK] Python: $Python"
    Write-Host "[OK] Running offline discovery dry-run only"
    Push-Location $ProjectRoot
    try {
        & $Python $RunPipeline --organism "Pseudomonas aeruginosa" --strain "not_specified" --workspace $WorkspaceDir --offline-only --dry-run
        if ($LASTEXITCODE -ne 0) {
            throw "Discovery dry-run failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

Write-Host "[OK] Demo preparation completed without writing global result folders."

