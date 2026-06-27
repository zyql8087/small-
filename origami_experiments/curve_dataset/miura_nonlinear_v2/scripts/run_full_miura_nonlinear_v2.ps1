param(
    [int]$StartIndex = 1,
    [int]$EndIndex = 2000,
    [int]$BatchSize = 500,
    [int]$CurvePoints = 80,
    [double]$TargetLinearDisplacement = 0.015,
    [double]$MaxFinalLoad = 10000,
    [string]$PythonExe = "F:\Anaconda\envs\GMM\python.exe",
    [switch]$SkipFinalPack,
    [switch]$SkipSmokeTrain
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$experimentRoot = Split-Path -Parent $scriptRoot
$jobDir = Join-Path $experimentRoot "jobs_miura"
$curvesDir = Join-Path $experimentRoot "raw_curves"
$outputDir = Join-Path $experimentRoot "data"
$resultDir = Join-Path $experimentRoot "smoke_results"
$logDir = Join-Path $experimentRoot "logs"
$batchScript = Join-Path $scriptRoot "run_swomps_miura_nonlinear_batch.ps1"
$auditScript = Join-Path $scriptRoot "audit_curve_batch.py"
$plotScript = Join-Path $scriptRoot "plot_miura_nonlinear_curves.py"
$packScript = Join-Path $scriptRoot "build_curve_dataset_npz.py"
$trainScript = Join-Path $scriptRoot "smoke_train_curve_dataset.py"

New-Item -ItemType Directory -Force -Path $curvesDir, $outputDir, $resultDir, $logDir | Out-Null

$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runLog = Join-Path $logDir "full_run_$runStamp.log"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $runLog -Append
}

function Invoke-LoggedExternal {
    param(
        [string]$Name,
        [string]$LogPath,
        [scriptblock]$Command
    )

    Write-RunLog "START $Name"
    & $Command *>&1 | Tee-Object -FilePath $LogPath -Append
    $exitCode = if ($null -eq $global:LASTEXITCODE) { 0 } else { $global:LASTEXITCODE }
    Write-RunLog "END $Name exit_code=$exitCode"
    if ($exitCode -ne 0) {
        throw "$Name failed with exit code $exitCode. See $LogPath"
    }
}

function Count-Curves {
    return (Get-ChildItem -LiteralPath $curvesDir -Filter "miura_*.csv" -File | Measure-Object).Count
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}
if (-not (Test-Path -LiteralPath $batchScript)) {
    throw "Batch script not found: $batchScript"
}
if (-not (Test-Path -LiteralPath (Join-Path $jobDir "parameters.csv"))) {
    throw "Parameter CSV not found under: $jobDir"
}
if ($BatchSize -lt 1) {
    throw "BatchSize must be positive."
}

Write-RunLog "Miura nonlinear v2 full run started."
Write-RunLog "Experiment root: $experimentRoot"
Write-RunLog "Range: $StartIndex-$EndIndex; BatchSize=$BatchSize; CurvePoints=$CurvePoints"
Write-RunLog "TargetLinearDisplacement=$TargetLinearDisplacement; MaxFinalLoad=$MaxFinalLoad"
Write-RunLog "Existing CSV count before run: $(Count-Curves)"

for ($batchStart = $StartIndex; $batchStart -le $EndIndex; $batchStart += $BatchSize) {
    $batchEnd = [Math]::Min($batchStart + $BatchSize - 1, $EndIndex)
    $batchName = "{0:D4}_{1:D4}" -f $batchStart, $batchEnd
    $batchLog = Join-Path $logDir "batch_${batchName}_$runStamp.log"
    $auditLog = Join-Path $logDir "audit_${batchName}_$runStamp.log"
    $plotLog = Join-Path $logDir "plot_${batchName}_$runStamp.log"

    Invoke-LoggedExternal "simulation batch $batchName" $batchLog {
        powershell -NoProfile -ExecutionPolicy Bypass -File $batchScript `
            -StartIndex $batchStart `
            -EndIndex $batchEnd `
            -CurvePoints $CurvePoints `
            -TargetLinearDisplacement $TargetLinearDisplacement `
            -MaxFinalLoad $MaxFinalLoad
    }

    Write-RunLog "CSV count after batch ${batchName}: $(Count-Curves)"

    Invoke-LoggedExternal "audit cumulative $batchEnd samples" $auditLog {
        & $PythonExe $auditScript `
            --job-dir $jobDir `
            --curves-dir $curvesDir `
            --output-dir $resultDir `
            --curve-points $CurvePoints `
            --expected-samples $batchEnd `
            --audit-mode nonlinear `
            --min-mean-secant-change-ratio 0.08 `
            --min-max-secant-change-ratio 0.25 `
            --min-mean-linearity-error 0.08
    }

    Invoke-LoggedExternal "plot samples after batch $batchName" $plotLog {
        & $PythonExe $plotScript `
            --job-dir $jobDir `
            --curves-dir $curvesDir `
            --output-dir $resultDir `
            --max-samples 5
    }
}

if (-not $SkipFinalPack.IsPresent) {
    $packLog = Join-Path $logDir "pack_$runStamp.log"
    Invoke-LoggedExternal "pack full dataset" $packLog {
        & $PythonExe $packScript `
            --job-dir $jobDir `
            --curves-dir $curvesDir `
            --output-dir $outputDir `
            --split group_pattern_mn `
            --test-size 0.2 `
            --seed 42 `
            --curve-points $CurvePoints `
            --allow-partial
    }
}

if (-not $SkipSmokeTrain.IsPresent) {
    $trainLog = Join-Path $logDir "smoke_train_$runStamp.log"
    Invoke-LoggedExternal "smoke train full dataset" $trainLog {
        & $PythonExe $trainScript `
            --data-dir $outputDir `
            --result-dir $resultDir `
            --epochs 300 `
            --batch-size 16 `
            --hidden-dim 256 `
            --lr 1e-3 `
            --seed 42
    }
}

Write-RunLog "Miura nonlinear v2 full run finished. Final CSV count: $(Count-Curves)"
