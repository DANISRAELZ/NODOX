param(
    [string]$ProjectPath = "",
    [string]$ManifestPath = "",
    [string]$Organism = "",
    [string]$Strain = "",
    [string]$Workspace = "",
    [string]$Dataset = "",
    [string]$InputFile = "",
    [switch]$ImportDataset,
    [switch]$RunPipeline,
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

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
        Write-Host "Uso: .\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -ManifestPath <manifest.csv>"
        Write-Host "Para importar una capa: agregue -ImportDataset -Dataset <dataset> -InputFile <csv> -Workspace <workspace> -Organism <name>"
        Write-Host "Para correr pipeline: agregue -RunPipeline -Workspace <workspace> -Organism <name>"
        exit 2
    }
    $ManifestPath = Join-Path $ProjectPath "manifest.csv"
}

$Python = Resolve-Python -Preferred $PYTHON_EXE
Write-Host "[OK] Python: $Python"
Write-Host "[INFO] Manifest user_curated: $ManifestPath"
Write-Host "[INFO] Primero se valida estructura y procedencia. No se usaran demo/proxy/cache como datos reales."

& .\scripts\validate_user_curated_dataset.ps1 -ProjectPath $ProjectPath -ManifestPath $ManifestPath -PYTHON_EXE $Python
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] La validacion fallo. Corrija el paquete user_curated antes de importar o ejecutar analisis."
    exit $LASTEXITCODE
}

if ($ImportDataset) {
    if ([string]::IsNullOrWhiteSpace($Dataset) -or [string]::IsNullOrWhiteSpace($InputFile) -or [string]::IsNullOrWhiteSpace($Workspace)) {
        Write-Host "[ERROR] Para importar use -Dataset <dataset> -InputFile <csv> -Workspace <workspace>."
        exit 2
    }
    Write-Host "[INFO] Importando capa user_curated prevalidada: $Dataset"
    $args = @("import_dataset.py", "--workspace", $Workspace, "--dataset", $Dataset, "--input", $InputFile, "--validate-user-curated-manifest", $ManifestPath)
    if (-not [string]::IsNullOrWhiteSpace($Organism)) { $args += @("--organism", $Organism) }
    if (-not [string]::IsNullOrWhiteSpace($Strain)) { $args += @("--strain", $Strain) }
    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] La importacion fallo. Revise columnas, rutas y manifest."
        exit $LASTEXITCODE
    }
}

if ($RunPipeline) {
    if ([string]::IsNullOrWhiteSpace($Organism) -or [string]::IsNullOrWhiteSpace($Workspace)) {
        Write-Host "[ERROR] Para ejecutar analisis use -Organism <name> y -Workspace <workspace>."
        exit 2
    }
    Write-Host "[WARN] Ejecutando pipeline user_curated explicitamente solicitado."
    Write-Host "[WARN] Este paso genera resultados dentro del workspace indicado; no use rutas versionadas."
    $pipelineArgs = @("run_pipeline.py", "--organism", $Organism, "--workspace", $Workspace, "--mode", "compare", "--offline-only", "--no-write-taxon-cache")
    if (-not [string]::IsNullOrWhiteSpace($Strain)) { $pipelineArgs += @("--strain", $Strain) }
    & $Python @pipelineArgs
    exit $LASTEXITCODE
}

if (-not $ImportDataset -and -not $RunPipeline) {
    Write-Host "[OK] Paquete user_curated validado. No se ejecuto importacion ni pipeline."
    Write-Host "[NEXT] Para importar: use -ImportDataset con -Dataset, -InputFile y -Workspace."
    Write-Host "[NEXT] Para pipeline: use -RunPipeline solo despues de revision manual."
}
