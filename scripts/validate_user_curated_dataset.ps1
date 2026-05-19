param(
    [string]$ProjectPath = "",
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

function Read-CsvHeader {
    param([string]$PathValue)
    $firstLine = Get-Content -LiteralPath $PathValue -TotalCount 1
    if ([string]::IsNullOrWhiteSpace($firstLine)) { return @() }
    return $firstLine.Split(",") | ForEach-Object { $_.Trim() }
}

function Resolve-InputPath {
    param([string]$InputFile, [string]$ProjectPathValue)
    if ([string]::IsNullOrWhiteSpace($InputFile)) { return $null }
    $direct = $InputFile
    if ([System.IO.Path]::IsPathRooted($direct) -and (Test-Path -LiteralPath $direct)) { return $direct }
    $candidateRaw = Join-Path (Join-Path $ProjectPathValue "raw_inputs") $InputFile
    if (Test-Path -LiteralPath $candidateRaw) { return $candidateRaw }
    $candidateProject = Join-Path $ProjectPathValue $InputFile
    if (Test-Path -LiteralPath $candidateProject) { return $candidateProject }
    if (Test-Path -LiteralPath $direct) { return $direct }
    return $candidateRaw
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
        Write-Host "Uso: .\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>"
        Write-Host "   o: .\scripts\validate_user_curated_dataset.ps1 -ManifestPath <ruta_manifest.csv>"
        exit 2
    }
    $ManifestPath = Join-Path $ProjectPath "manifest.csv"
}
if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Split-Path -Parent $ManifestPath
}

$Python = Resolve-Python -Preferred $PYTHON_EXE
Write-Host "[OK] Python: $Python"
Write-Host "[INFO] Revisando manifest user_curated: $ManifestPath"
Write-Host "[INFO] Carpeta de trabajo: $ProjectPath"
Write-Host "[INFO] Esta validacion no importa datos, no ejecuta pipeline ni scoring."

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Host "[ERROR] No existe el manifest: $ManifestPath"
    exit 1
}

& $Python scripts\validate_user_curated_manifest.py $ManifestPath
$manifestExit = $LASTEXITCODE

$errors = 0
$warnings = 0
if ($manifestExit -ne 0) { $errors += 1 }

$rows = Import-Csv -LiteralPath $ManifestPath
if ($rows.Count -eq 0) {
    Write-Host "[ERROR] El manifest no tiene filas de datasets."
    exit 1
}

$requiredByDataset = @{
    "functional_annotations" = @("organism", "strain", "protein_id", "gene", "functional_annotation", "source_database", "evidence_status")
    "gene_list" = @("organism", "strain", "protein_id", "gene", "source_database", "evidence_status")
    "conservation" = @("organism", "strain", "protein_id", "gene", "conservation_scope", "source_database", "evidence_status")
    "virulence" = @("protein_id", "gene", "virulence_score", "virulence_factor", "database")
    "essentiality" = @("protein_id", "gene", "essential", "evidence", "database")
    "external_sources" = @("organism", "strain", "protein_id", "gene", "source_database", "source_record_id", "evidence_status")
    "manual_curation" = @("organism", "strain", "protein_id", "gene", "curator_name", "curation_decision", "evidence_status")
}
$optionalByDataset = @{
    "functional_annotations" = @("product_name", "pathway", "go_terms", "ec_number", "curator_notes")
    "gene_list" = @("locus_tag", "gene_description", "curator_notes")
    "conservation" = @("core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden", "curator_notes")
    "external_sources" = @("source_version", "export_date", "evidence_type", "source_url_or_reference", "curator_notes")
    "manual_curation" = @("curation_date", "evidence_summary", "source_database", "reference_or_note", "curator_notes")
}

foreach ($row in $rows) {
    $datasetId = ($row.dataset_id | ForEach-Object { "$_".Trim() })
    $inputFile = ($row.input_file | ForEach-Object { "$_".Trim() })
    $inputSchema = ($row.input_schema | ForEach-Object { "$_".Trim() })
    Write-Host "[INFO] Revisando dataset: $datasetId"
    Write-Host "[INFO] Archivo declarado: $inputFile"

    if ($row.source_type -ne "user_curated") {
        Write-Host "[ERROR] source_type debe ser user_curated para datos reales. Valor actual: $($row.source_type)"
        $errors += 1
    }

    $inputPath = Resolve-InputPath -InputFile $inputFile -ProjectPathValue $ProjectPath
    if (-not (Test-Path -LiteralPath $inputPath)) {
        Write-Host "[ERROR] No se encontro el archivo de entrada: $inputPath"
        Write-Host "[NEXT] Coloque el archivo real en raw_inputs/ o corrija input_file en el manifest."
        $errors += 1
        continue
    }

    $header = @(Read-CsvHeader -PathValue $inputPath)
    if ($header.Count -eq 0) {
        Write-Host "[ERROR] El archivo no tiene encabezado CSV legible: $inputPath"
        $errors += 1
        continue
    }

    $schemaPath = $inputSchema
    if (-not [string]::IsNullOrWhiteSpace($schemaPath) -and -not [System.IO.Path]::IsPathRooted($schemaPath)) {
        $schemaPath = Join-Path $ProjectRoot $schemaPath
    }
    if (-not [string]::IsNullOrWhiteSpace($schemaPath) -and (Test-Path -LiteralPath $schemaPath)) {
        $schemaHeader = @(Read-CsvHeader -PathValue $schemaPath)
        $missingFromSchema = @($schemaHeader | Where-Object { $_ -notin $header })
        if ($missingFromSchema.Count -gt 0) {
            Write-Host "[WARN] Columnas de la plantilla ausentes en ${inputFile}: $($missingFromSchema -join ', ')"
            $warnings += 1
        }
    } else {
        Write-Host "[WARN] No se encontro input_schema para comparar encabezados: $inputSchema"
        $warnings += 1
    }

    $requiredColumns = @()
    if ($requiredByDataset.ContainsKey($datasetId)) { $requiredColumns = $requiredByDataset[$datasetId] }
    $missingRequired = @($requiredColumns | Where-Object { $_ -notin $header })
    if ($missingRequired.Count -gt 0) {
        Write-Host "[ERROR] Columnas requeridas faltantes en ${inputFile}: $($missingRequired -join ', ')"
        Write-Host "[NEXT] Agregue estas columnas o use la plantilla correspondiente en data_templates/."
        $errors += 1
    } else {
        Write-Host "[OK] Columnas requeridas presentes para $datasetId."
    }

    if ($optionalByDataset.ContainsKey($datasetId)) {
        $missingOptional = @($optionalByDataset[$datasetId] | Where-Object { $_ -notin $header })
        if ($missingOptional.Count -gt 0) {
            Write-Host "[INFO] Columnas opcionales ausentes en ${inputFile}: $($missingOptional -join ', ')"
        }
    }

    $placeholderLines = Select-String -LiteralPath $inputPath -Pattern "<[^>]+>" -SimpleMatch:$false
    if ($placeholderLines) {
        Write-Host "[WARN] Se detectaron valores tipo placeholder en $inputFile. Reemplacelos antes de interpretar resultados."
        $warnings += 1
    }

    $sourceLikeColumns = @("source_type", "source_database", "database", "evidence_source_type")
    foreach ($column in $sourceLikeColumns) {
        if ($header -contains $column) {
            $values = Import-Csv -LiteralPath $inputPath | Select-Object -ExpandProperty $column -ErrorAction SilentlyContinue
            $mixed = @($values | Where-Object { "$_".Trim().ToLowerInvariant() -in @("demo", "proxy", "cache", "controlled_reference", "online") })
            if ($mixed.Count -gt 0) {
                Write-Host "[ERROR] $inputFile contiene valores no user_curated en ${column}: $($mixed | Select-Object -Unique)"
                Write-Host "[NEXT] Separe esas filas o marque la procedencia sin usarlas como evidencia real."
                $errors += 1
            }
        }
    }
}

if ($errors -gt 0) {
    Write-Host "[ERROR] Validacion user_curated terminada con $errors problema(s) y $warnings advertencia(s)."
    exit 1
}

Write-Host "[OK] Validacion user_curated completada con $warnings advertencia(s)."
Write-Host "[NEXT] Si todo fue revisado manualmente, puede importar una capa con import_dataset.py --validate-user-curated-manifest."
exit 0
