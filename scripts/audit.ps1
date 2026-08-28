[CmdletBinding()]
param(
    [switch]$WarnOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$root = Split-Path $PSScriptRoot -Parent
$results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param(
        [string]$Name,
        [ValidateSet("PASS", "WARN", "FAIL")]
        [string]$Status,
        [string]$Detail
    )

    $null = $results.Add([pscustomobject]@{
        Check = $Name
        Status = $Status
        Detail = $Detail
    })
}

function Invoke-NativeCheck {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments,
        [ValidateSet("WARN", "FAIL")]
        [string]$FailureStatus = "FAIL"
    )

    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $Executable @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    $outputLines = @($output | ForEach-Object { "$_" })
    if ($outputLines.Count -le 9) {
        $detail = $outputLines -join " | "
    }
    else {
        $detail = @(
            $outputLines | Select-Object -First 5
            "..."
            $outputLines | Select-Object -Last 4
        ) -join " | "
    }
    if (-not $detail) {
        $detail = "exit $exitCode"
    }
    Add-Result $Name $(if ($exitCode -eq 0) { "PASS" } else { $FailureStatus }) $detail
}

Push-Location $root
try {
    $themeCount = @(Get-ChildItem -LiteralPath "prompt_system/themes" -Filter "*.yaml" -File).Count
    $layoutCount = @(Get-ChildItem -LiteralPath "prompt_system/layouts" -Filter "*.yaml" -File).Count
    $styleCaseCount = @(Get-ChildItem -LiteralPath "prompt_system/style_cases" -Filter "*.yaml" -File).Count
    $adapterDirectories = @(
        "prompt_system/renderers/image2/themes",
        "prompt_system/renderers/image2/layouts",
        "prompt_system/renderers/html/themes",
        "prompt_system/renderers/html/layouts",
        "prompt_system/renderers/pptx/themes",
        "prompt_system/renderers/pptx/layouts"
    )
    $adapterCount = @(
        foreach ($adapterDirectory in $adapterDirectories) {
            Get-ChildItem -LiteralPath $adapterDirectory -Filter "*.yaml" -File
        }
    ).Count
    $expectedAdapters = 3 * ($themeCount + $layoutCount)
    Add-Result "Core and adapter counts" `
        $(if ($adapterCount -eq $expectedAdapters) { "PASS" } else { "FAIL" }) `
        "themes=$themeCount layouts=$layoutCount style_cases=$styleCaseCount adapters=$adapterCount expected=$expectedAdapters"

    $matrix = Get-Content -Raw -Encoding utf8 -LiteralPath "artifacts/renderer-matrix/matrix.json" | ConvertFrom-Json
    $matrixMatches = (
        [int]$matrix.counts.themes -eq $themeCount -and
        [int]$matrix.counts.layouts -eq $layoutCount -and
        [int]$matrix.counts.combinations_per_renderer -eq ($themeCount * $layoutCount)
    )
    Add-Result "Renderer matrix registry" `
        $(if ($matrixMatches) { "PASS" } else { "FAIL" }) `
        "matrix=$($matrix.counts.themes)x$($matrix.counts.layouts) combinations=$($matrix.counts.combinations_per_renderer)"

    Invoke-NativeCheck "Renderer adapters hash" "python" @("scripts/generate_renderer_adapters.py", "--check")
    Invoke-NativeCheck "Canonical HTML editor asset" "python" @("scripts/sync_editor_asset.py")
    Invoke-NativeCheck "HTML Preset registry and Gallery" "python" @("scripts/html_preset_registry.py")
    Invoke-NativeCheck "HTML Preset selection policy" "python" @("scripts/qa_html_preset_selection_policy.py")
    Invoke-NativeCheck "HTML Layout scaffold composition" "python" @("scripts/qa_html_layout_scaffold_composition.py")
    Invoke-NativeCheck "Layout Gallery triptych coverage" "python" @("scripts/verify_layout_gallery_triptychs.py")
    Invoke-NativeCheck "Layout preview strict QA" "python" @("scripts/verify_layout_preview_qa.py") "WARN"
    Invoke-NativeCheck "Git diff format" "git" @("diff", "--check")
    Invoke-NativeCheck "Current branch upstream" "git" @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") "WARN"

    $dependencyFiles = @("requirements.txt", "package.json", "package-lock.json")
    $missingDependencyFiles = @($dependencyFiles | Where-Object { -not (Test-Path -LiteralPath $_) })
    $hasAuditWorkflow = Test-Path -LiteralPath ".github/workflows/repository-audit.yml"
    Add-Result "Dependency manifests and CI" `
        $(if ($missingDependencyFiles.Count -eq 0 -and $hasAuditWorkflow) { "PASS" } else { "FAIL" }) `
        "missing=$($missingDependencyFiles -join ',') audit_workflow=$hasAuditWorkflow"

    $oneOffScripts = @(Get-ChildItem -LiteralPath "scripts" -File | Where-Object Name -Like "_codex*")
    Add-Result "One-off migration boundary" `
        $(if ($oneOffScripts.Count -eq 0) { "PASS" } else { "FAIL" }) `
        "scripts_root_codex_one_offs=$($oneOffScripts.Count)"

    $codexConfig = Get-Content -Raw -Encoding utf8 -LiteralPath ".codex/config.toml"
    $forcesFullAccess = $codexConfig -match '(?m)^\s*sandbox_mode\s*=\s*["'']danger-full-access["'']'
    Add-Result "Shared Codex permission boundary" `
        $(if ($forcesFullAccess) { "FAIL" } else { "PASS" }) `
        "forces_danger_full_access=$forcesFullAccess"

    $qaSummary = "artifacts/qa/renderer-matrix/summary.json"
    Add-Result "Renderer matrix full QA" `
        $(if (Test-Path -LiteralPath $qaSummary) { "PASS" } else { "WARN" }) `
        $(if (Test-Path -LiteralPath $qaSummary) { $qaSummary } else { "summary missing; full HTML/PPTX matrix is unverified" })

    $themeLabQa = "artifacts/theme-demos/html-theme-lab/qa/theme-lab-verification.json"
    if (Test-Path -LiteralPath $themeLabQa) {
        $themeLabReport = Get-Content -Raw -Encoding utf8 -LiteralPath $themeLabQa | ConvertFrom-Json
        Add-Result "HTML Theme Lab recorded QA" `
            $(if ($themeLabReport.pass) { "PASS" } else { "WARN" }) `
            "pass=$($themeLabReport.pass) failures=$(@($themeLabReport.failures).Count) report=$themeLabQa"
    }
    else {
        Add-Result "HTML Theme Lab recorded QA" "WARN" "report missing: $themeLabQa"
    }

    $backgroundSetCount = @(Get-ChildItem -LiteralPath "prompt_system/pptx_background_sets" -Filter "*.yaml" -File).Count
    Add-Result "PPTX background-set sources" `
        $(if ($backgroundSetCount -eq $themeCount) { "PASS" } else { "WARN" }) `
        "background_sets=$backgroundSetCount themes=$themeCount"

    $gitlinks = @(git ls-files --stage | Where-Object { $_ -match '^160000\s' })
    $hasGitmodules = Test-Path -LiteralPath ".gitmodules"
    Add-Result "Gitlink management" `
        $(if ($gitlinks.Count -eq 0 -or $hasGitmodules) { "PASS" } else { "WARN" }) `
        "gitlinks=$($gitlinks.Count) .gitmodules=$hasGitmodules"

    $trackedWranglerCache = @(git ls-files ".wrangler/cache/*")
    Add-Result "Wrangler local metadata" `
        $(if ($trackedWranglerCache.Count -eq 0) { "PASS" } else { "WARN" }) `
        "tracked_cache_files=$($trackedWranglerCache.Count)"

    $worktreeLines = @(git worktree list --porcelain)
    $worktreePaths = @($worktreeLines | Where-Object { $_ -like "worktree *" } | ForEach-Object { $_.Substring(9) })
    $dirtyDescriptions = [System.Collections.Generic.List[string]]::new()
    foreach ($worktreePath in $worktreePaths) {
        $dirtyCount = @(git -C $worktreePath status --porcelain --untracked-files=all).Count
        if ($dirtyCount -gt 0) {
            $null = $dirtyDescriptions.Add("$worktreePath ($dirtyCount)")
        }
    }
    Add-Result "Git worktree state" `
        $(if ($dirtyDescriptions.Count -eq 0) { "PASS" } else { "WARN" }) `
        $(if ($dirtyDescriptions.Count -eq 0) { "all clean" } else { $dirtyDescriptions -join "; " })
}
finally {
    Pop-Location
}

$results | Format-Table -AutoSize -Wrap

$failCount = @($results | Where-Object Status -eq "FAIL").Count
$warnCount = @($results | Where-Object Status -eq "WARN").Count
Write-Host ""
Write-Host "Audit summary: PASS=$(@($results | Where-Object Status -eq 'PASS').Count) WARN=$warnCount FAIL=$failCount"

if ($failCount -gt 0 -and -not $WarnOnly) {
    exit 1
}
exit 0
