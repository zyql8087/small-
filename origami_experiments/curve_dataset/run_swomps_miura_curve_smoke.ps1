param(
    [int]$StartIndex = 1,
    [int]$EndIndex = 10,
    [int]$CurvePoints = 30,
    [double]$FinalLoad = 3,
    [string]$MatlabExe = "F:\Polyspace\R2020b\bin\matlab.exe",
    [string]$ProjectRoot = "F:\small++",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

$scriptDir = Join-Path $ProjectRoot "origami_experiments\curve_dataset\matlab"
$parameterCsv = Join-Path $ProjectRoot "origami_experiments\curve_dataset\jobs_miura\parameters.csv"
$outputDir = Join-Path $ProjectRoot "origami_experiments\curve_dataset\raw_curves_miura"
$simulatorRoot = Join-Path $ProjectRoot "external\OrigamiSimulator"
$overwriteMatlab = if ($Overwrite.IsPresent) { "true" } else { "false" }

if (-not (Test-Path -LiteralPath $MatlabExe)) {
    throw "MATLAB executable not found: $MatlabExe"
}
if (-not (Test-Path -LiteralPath $parameterCsv)) {
    throw "Parameter CSV not found: $parameterCsv"
}
if (-not (Test-Path -LiteralPath $simulatorRoot)) {
    throw "OrigamiSimulator not found: $simulatorRoot"
}

$matlabCommand = @"
addpath('$scriptDir');
GenerateOrigamiForceDisplacementCurves( ...
    '$parameterCsv', ...
    '$outputDir', ...
    'SimulatorRoot', '$simulatorRoot', ...
    'CurvePoints', $CurvePoints, ...
    'FinalLoad', $FinalLoad, ...
    'FinalLoadMode', 'fixed', ...
    'StartIndex', $StartIndex, ...
    'EndIndex', $EndIndex, ...
    'Overwrite', $overwriteMatlab, ...
    'RequireMiuraOnly', true);
"@

& $MatlabExe -batch $matlabCommand
