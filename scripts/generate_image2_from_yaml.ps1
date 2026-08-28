# Generate one slide preview image from an assembled YAML using the local Image2 draw skill.
#
# Example:
#   powershell -File scripts\generate_image2_from_yaml.ps1 `
#     -YamlPath artifacts\generated-prompts\staging\funnel-4-consulting-burgundy.assembled.yaml `
#     -OutputPath artifacts\deploy\layout-previews-staging\funnel-4-consulting-burgundy-image2.png `
#     -Name funnel-4-consulting-burgundy-image2

param(
    [Parameter(Mandatory = $true)]
    [string]$YamlPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$Name = "",
    [string]$Size = "1536x1024",
    [ValidateSet("low", "medium", "high", "auto")]
    [string]$Quality = "low",
    [string]$DrawScript = "$env:USERPROFILE\.codex\skills\cover-image\draw.py"
)

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$yamlFullPath = Resolve-Path -LiteralPath (Join-Path $root $YamlPath)
$outputFullPath = Join-Path $root $OutputPath
$outDir = Split-Path $outputFullPath -Parent

if (-not (Test-Path -LiteralPath $DrawScript)) {
    throw "Image2 draw script not found: $DrawScript"
}

if ([string]::IsNullOrWhiteSpace($Name)) {
    $Name = [IO.Path]::GetFileNameWithoutExtension($OutputPath)
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$yamlText = [IO.File]::ReadAllText($yamlFullPath, [Text.Encoding]::UTF8)
$prompt = @"
Create one polished 16:9 presentation slide image from the assembled YAML below.

Use the YAML as the authoritative design specification. Preserve the layout, content hierarchy, visual theme, typography mood, palette, safe-zone rules, and closing design intent. Render it as a finished presentation preview image, not as a wireframe, not as a generic infographic template.

If the YAML contains Chinese text, keep the Chinese text readable and as close as possible to the exact provided wording. Keep all important text inside slide-safe margins.

ASSEMBLED YAML:
$yamlText
"@

$before = @{}
Get-ChildItem -LiteralPath $outDir -Filter "$Name*.png" -ErrorAction SilentlyContinue | ForEach-Object {
    $before[$_.FullName] = $true
}

Push-Location $root
try {
    & python $DrawScript $prompt --size $Size --quality $Quality --name $Name --outdir $outDir
}
finally {
    Pop-Location
}

$latest = Get-ChildItem -LiteralPath $outDir -Filter "$Name*.png" |
    Where-Object { -not $before.ContainsKey($_.FullName) } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    $latest = Get-ChildItem -LiteralPath $outDir -Filter "$Name*.png" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

if (-not $latest) {
    throw "Image2 generation finished but no PNG was found for prefix: $Name"
}

Copy-Item -LiteralPath $latest.FullName -Destination $outputFullPath -Force
Write-Host "Generated timestamped image: $($latest.FullName)"
Write-Host "Copied stable output to: $outputFullPath"
