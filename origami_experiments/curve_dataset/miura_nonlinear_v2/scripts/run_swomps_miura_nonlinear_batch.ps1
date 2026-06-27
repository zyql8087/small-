param(
    [int]$StartIndex = 1,
    [int]$EndIndex = 50,
    [int]$CurvePoints = 80,
    [double]$FinalLoad = 3,
    [ValidateSet("fixed", "stiffness_scaled")]
    [string]$FinalLoadMode = "stiffness_scaled",
    [double]$TargetLinearDisplacement = 0.015,
    [double]$MaxFinalLoad = 10000,
    [string]$MatlabExe = "F:\Polyspace\R2020b\bin\matlab.exe",
    [string]$ProjectRoot = "F:\small++",
    [string]$ParameterCsv = "",
    [string]$OutputDir = "",
    [bool]$RequirePhysics = $true,
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$experimentRoot = Split-Path -Parent $scriptRoot
$scriptDir = Join-Path $experimentRoot "matlab"
if ([string]::IsNullOrWhiteSpace($ParameterCsv)) {
    $ParameterCsv = Join-Path $experimentRoot "jobs_miura\parameters.csv"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $experimentRoot "raw_curves"
}
$simulatorRoot = Join-Path $ProjectRoot "external\OrigamiSimulator"
$overwriteMatlab = if ($Overwrite.IsPresent) { "true" } else { "false" }

if (-not (Test-Path -LiteralPath $MatlabExe)) {
    throw "MATLAB executable not found: $MatlabExe"
}
if (-not (Test-Path -LiteralPath $ParameterCsv)) {
    throw "Parameter CSV not found: $ParameterCsv"
}
if (-not (Test-Path -LiteralPath $simulatorRoot)) {
    throw "OrigamiSimulator not found: $simulatorRoot"
}

$matlabCommand = @"
addpath('$scriptDir');
GenerateOrigamiForceDisplacementCurves( ...
    '$ParameterCsv', ...
    '$OutputDir', ...
    'SimulatorRoot', '$simulatorRoot', ...
    'CurvePoints', $CurvePoints, ...
    'FinalLoad', $FinalLoad, ...
    'FinalLoadMode', '$FinalLoadMode', ...
    'TargetLinearDisplacement', $TargetLinearDisplacement, ...
    'MaxFinalLoad', $MaxFinalLoad, ...
    'StartIndex', $StartIndex, ...
    'EndIndex', $EndIndex, ...
    'Overwrite', $overwriteMatlab, ...
    'RequireMiuraOnly', true, ...
    'RequirePhysics', $($RequirePhysics.ToString().ToLower()));
"@

& $MatlabExe -batch $matlabCommand
