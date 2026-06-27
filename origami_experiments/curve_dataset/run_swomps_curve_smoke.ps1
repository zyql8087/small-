param(
    [int]$StartIndex = 1,
    [int]$EndIndex = 20,
    [int]$CurvePoints = 30,
    [string]$MatlabExe = "F:\Polyspace\R2020b\bin\matlab.exe",
    [string]$ProjectRoot = "F:\small++",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

$scriptDir = Join-Path $ProjectRoot "origami_experiments\curve_dataset\matlab"
$parameterCsv = Join-Path $ProjectRoot "origami_experiments\curve_dataset\jobs\parameters.csv"
$outputDir = Join-Path $ProjectRoot "origami_experiments\curve_dataset\raw_curves"
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
    'FinalLoadMode', 'fixed', ...
    'StartIndex', $StartIndex, ...
    'EndIndex', $EndIndex, ...
    'Overwrite', $overwriteMatlab);
"@

& $MatlabExe -batch $matlabCommand
