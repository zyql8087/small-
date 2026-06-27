$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$experimentRoot = Split-Path -Parent $scriptRoot
$logDir = Join-Path $experimentRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$launchStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$launchLog = Join-Path $logDir "launcher_$launchStamp.log"
$runner = Join-Path $scriptRoot "run_full_miura_nonlinear_v2.ps1"

function Write-LaunchLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $launchLog -Append
}

try {
    Write-LaunchLog "Launcher entered."
    Write-LaunchLog "Runner: $runner"

    & $runner `
        -StartIndex 1 `
        -EndIndex 2000 `
        -BatchSize 500 `
        -CurvePoints 80 `
        -TargetLinearDisplacement 0.015 `
        -MaxFinalLoad 10000

    Write-LaunchLog "Launcher finished successfully."
} catch {
    Write-LaunchLog "Launcher failed: $($_.Exception.Message)"
    Write-LaunchLog $_.ScriptStackTrace
    throw
}
