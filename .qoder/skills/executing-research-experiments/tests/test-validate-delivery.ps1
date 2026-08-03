$ErrorActionPreference = 'Stop'

$testsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillRoot = Split-Path -Parent $testsRoot
$fixturesRoot = Join-Path $testsRoot 'fixtures'
$validatorPath = Join-Path $skillRoot 'scripts\validate-delivery.ps1'

function Assert-Equal {
    param($Actual, $Expected, [string]$Message)
    if ($Actual -ne $Expected) { throw "$Message. Expected '$Expected', got '$Actual'." }
}

function Assert-Nonzero {
    param([int]$Actual, [string]$Message)
    if ($Actual -eq 0) { throw "$Message. Expected a nonzero exit code, got '0'." }
}

function Assert-Contains {
    param([string]$Actual, [string]$Expected, [string]$Message)
    if ($Actual -notmatch [regex]::Escape($Expected)) {
        throw "$Message. Expected stderr to contain '$Expected'. Actual stderr: $Actual"
    }
}

function Get-CaseSnapshot {
    param([string]$FixtureRoot)
    $records = foreach ($item in Get-ChildItem -LiteralPath $FixtureRoot -Recurse -Force | Sort-Object FullName) {
        $relative = $item.FullName.Substring($FixtureRoot.Length).TrimStart([char[]]@('\', '/'))
        if ($item.PSIsContainer) { "$relative|directory|0|" }
        else { "$relative|file|$($item.Length)|$((Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash.ToLowerInvariant())" }
    }
    return @($records)
}

function Assert-SnapshotUnchanged {
    param($Before, $After, [string]$CaseName)
    $difference = @(Compare-Object -ReferenceObject @($Before) -DifferenceObject @($After))
    if ($difference.Count -ne 0) {
        $details = $difference | ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }
        throw "validator modified fixture '$CaseName': $($details -join '; ')"
    }
}

function Invoke-ValidatorCase {
    param([string]$CaseName)
    $fixtureRoot = Join-Path $fixturesRoot $CaseName
    $before = Get-CaseSnapshot -FixtureRoot $fixtureRoot
    $process = New-Object System.Diagnostics.Process
    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = (Get-Command powershell.exe).Source
        $startInfo.Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$validatorPath`" -DeliveryRoot `"$fixtureRoot`""
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $process.StartInfo = $startInfo
        if (-not $process.Start()) { throw "failed to start validator case '$CaseName'" }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $result = [pscustomobject]@{
            CaseName = $CaseName
            ExitCode = $process.ExitCode
            Stdout = $stdoutTask.Result.TrimEnd()
            Stderr = $stderrTask.Result.TrimEnd()
        }
    }
    finally {
        $process.Dispose()
        $after = Get-CaseSnapshot -FixtureRoot $fixtureRoot
        Assert-SnapshotUnchanged -Before $before -After $after -CaseName $CaseName
    }
    return $result
}

function Format-CaseContext {
    param($Result)
    return "case=$($Result.CaseName)`nSTDOUT:`n$($Result.Stdout)`nSTDERR:`n$($Result.Stderr)"
}

$valid = Invoke-ValidatorCase -CaseName 'valid'
Assert-Equal $valid.ExitCode 0 "valid fixture exit code`n$(Format-CaseContext $valid)"
Write-Output 'PASS valid'

$missingEvidence = Invoke-ValidatorCase -CaseName 'missing-evidence'
Assert-Nonzero $missingEvidence.ExitCode "missing-evidence fixture exit code`n$(Format-CaseContext $missingEvidence)"
Assert-Contains $missingEvidence.Stderr 'evidence-report.md' "missing-evidence diagnostic`n$(Format-CaseContext $missingEvidence)"
Write-Output 'PASS missing-evidence'

$idMismatch = Invoke-ValidatorCase -CaseName 'id-mismatch'
Assert-Nonzero $idMismatch.ExitCode "id-mismatch fixture exit code`n$(Format-CaseContext $idMismatch)"
Assert-Contains $idMismatch.Stderr 'task_id mismatch' "id-mismatch diagnostic`n$(Format-CaseContext $idMismatch)"
Write-Output 'PASS id-mismatch'

$placeholder = Invoke-ValidatorCase -CaseName 'placeholder'
Assert-Nonzero $placeholder.ExitCode "placeholder fixture exit code`n$(Format-CaseContext $placeholder)"
Assert-Contains $placeholder.Stderr 'unresolved placeholder' "placeholder diagnostic`n$(Format-CaseContext $placeholder)"
Write-Output 'PASS placeholder'

Write-Output 'All delivery validator tests passed: 4/4'
