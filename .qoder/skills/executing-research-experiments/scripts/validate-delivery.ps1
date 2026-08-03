param(
    [Parameter(Mandatory = $true)]
    [string]$DeliveryRoot
)

$ErrorActionPreference = 'Stop'
$findings = New-Object System.Collections.Generic.List[string]

function Add-Finding {
    param([string]$Message)
    $script:findings.Add($Message)
}

if (-not (Test-Path -LiteralPath $DeliveryRoot -PathType Container)) {
    Add-Finding "delivery directory does not exist: $DeliveryRoot"
}
else {
    $resolvedRoot = (Resolve-Path -LiteralPath $DeliveryRoot).Path
    $requiredNames = @('evidence-report.md', 'review-ledger.md', 'experiment-manifest.yaml')
    $contents = @{}

    foreach ($name in $requiredNames) {
        $filePath = Join-Path $resolvedRoot $name
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            Add-Finding "missing required file: $name"
            continue
        }
        $contents[$name] = Get-Content -LiteralPath $filePath -Raw
    }

    foreach ($name in @($contents.Keys)) {
        if ($contents[$name] -match '(?i)(?<![A-Za-z0-9_])(TODO|TBD|PLACEHOLDER)(?![A-Za-z0-9_])') {
            Add-Finding "unresolved placeholder in $name"
        }
    }

    $taskId = $null
    if ($contents.ContainsKey('experiment-manifest.yaml')) {
        $match = [regex]::Match($contents['experiment-manifest.yaml'], '(?m)^task_id:\s*["'']?([^"''\r\n]+)')
        if (-not $match.Success) {
            Add-Finding 'manifest task_id is missing'
        }
        else {
            $taskId = $match.Groups[1].Value.Trim()
        }
    }

    foreach ($name in @('evidence-report.md', 'review-ledger.md')) {
        if (-not $contents.ContainsKey($name)) { continue }
        $match = [regex]::Match($contents[$name], '(?mi)^task_id:\s*["'']?([^"''\r\n]+)')
        if (-not $match.Success) {
            Add-Finding "task_id is missing from $name"
        }
        elseif ($null -ne $taskId -and $match.Groups[1].Value.Trim() -ne $taskId) {
            Add-Finding "task_id mismatch in $name"
        }
    }

    if ($contents.ContainsKey('evidence-report.md')) {
        foreach ($heading in @('Environment', 'Commands and exit codes', 'Artifacts and hashes', 'Unresolved issues', 'Git state')) {
            if ($contents['evidence-report.md'] -notmatch "(?m)^## $([regex]::Escape($heading))\s*$") {
                Add-Finding "missing evidence heading: ## $heading"
            }
        }
    }

    if ($contents.ContainsKey('review-ledger.md')) {
        foreach ($heading in @('Stage 1', 'Stage 2', 'Findings', 'Final decision')) {
            if ($contents['review-ledger.md'] -notmatch "(?m)^## $([regex]::Escape($heading))\s*$") {
                Add-Finding "missing review heading: ## $heading"
            }
        }
    }
}

if ($findings.Count -ne 0) {
    foreach ($finding in $findings) { [Console]::Error.WriteLine($finding) }
    exit 1
}

Write-Output "Delivery validation passed for $taskId"
exit 0
