param(
    [Parameter(Mandatory = $true)][string]$InputPptx,
    [Parameter(Mandatory = $true)][string]$SelectionManifest,
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$ReportPath
)

$ErrorActionPreference = 'Stop'
$pptxPath = (Resolve-Path -LiteralPath $InputPptx).Path
$selectionPath = (Resolve-Path -LiteralPath $SelectionManifest).Path
$rootPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
$reportFull = [IO.Path]::GetFullPath($ReportPath)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($reportFull)) | Out-Null
$selection = Get-Content -LiteralPath $selectionPath -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100

function Convert-HexToOfficeRgb([string]$Hex) {
    $text = $Hex.TrimStart('#')
    if ($text.Length -ne 6) { throw "Expected six-digit color, received $Hex" }
    $r = [Convert]::ToInt32($text.Substring(0, 2), 16)
    $g = [Convert]::ToInt32($text.Substring(2, 2), 16)
    $b = [Convert]::ToInt32($text.Substring(4, 2), 16)
    return $r + ($g -shl 8) + ($b -shl 16)
}

function Convert-Region($Region, [double]$SlideWidth, [double]$SlideHeight, $Offset) {
    $dx = if ($null -ne $Offset) { [double]$Offset.dx } else { 0.0 }
    $dy = if ($null -ne $Offset) { [double]$Offset.dy } else { 0.0 }
    return @(
        (([double]$Region[0] + $dx) / 100.0 * $SlideWidth)
        (([double]$Region[1] + $dy) / 100.0 * $SlideHeight)
        ([double]$Region[2] / 100.0 * $SlideWidth)
        ([double]$Region[3] / 100.0 * $SlideHeight)
    )
}

function Encode-Offset([double]$Value) {
    return ([string]$Value).Replace('-', 'm').Replace('.', 'p')
}

function Get-MaterializedLayoutName($SlideSpec) {
    $base = [string]$SlideSpec.layout_name
    $offset = $SlideSpec.composition_offset_percent
    $dx = if ($null -ne $offset) { [double]$offset.dx } else { 0.0 }
    $dy = if ($null -ne $offset) { [double]$offset.dy } else { 0.0 }
    if ([Math]::Abs($dx) -lt 0.000000001 -and [Math]::Abs($dy) -lt 0.000000001) { return $base }
    return "$base--offset-$(Encode-Offset $dx)-$(Encode-Offset $dy)"
}

function Find-Layout($Presentation, [string]$Name) {
    foreach ($design in $Presentation.Designs) {
        foreach ($layout in $design.SlideMaster.CustomLayouts) {
            if ($layout.Name -eq $Name) { return $layout }
        }
    }
    throw "Custom Layout not found: $Name"
}

function Set-NoBullet($Shape) {
    if ($Shape.HasTextFrame -and $Shape.TextFrame2.HasText) {
        $Shape.TextFrame2.TextRange.ParagraphFormat.Bullet.Visible = 0
    }
}

$backgroundSet = $selection.background_selection.selected
if ($null -eq $backgroundSet) { throw 'Selection manifest has no selected background set' }
$backgroundByRole = @{}
foreach ($role in $backgroundSet.roles) { $backgroundByRole[[string]$role.id] = [string]$role.asset }

$app = New-Object -ComObject PowerPoint.Application
$layoutRows = [Collections.Generic.List[object]]::new()
try {
    $app.DisplayAlerts = 1
    $presentation = $app.Presentations.Open($pptxPath, $false, $false, $false)
    try {
        $slideWidth = [double]$presentation.PageSetup.SlideWidth
        $slideHeight = [double]$presentation.PageSetup.SlideHeight
        foreach ($slideSpec in $selection.slides) {
            $layoutName = Get-MaterializedLayoutName $slideSpec
            $layout = Find-Layout $presentation $layoutName
            $surfaceNames = @()
            $surfaceIndex = 0
            foreach ($surface in @($slideSpec.surfaces | Where-Object { $null -ne $_ })) {
                $id = if ($surface.id) { [string]$surface.id } else { [string]$surfaceIndex }
                $surfaceNames += "surface-$id"
                $surfaceIndex += 1
            }
            $ruleNames = @($slideSpec.rules | ForEach-Object { "rule-$($_.id)" })
            for ($index = $layout.Shapes.Count; $index -ge 1; $index -= 1) {
                $shape = $layout.Shapes.Item($index)
                if ($shape.Type -eq 13 -or $surfaceNames -contains $shape.Name -or $ruleNames -contains $shape.Name) {
                    $shape.Delete()
                }
            }

            $role = [string]$slideSpec.background_role
            if (-not $backgroundByRole.ContainsKey($role)) { throw "Background role not found: $role" }
            $assetPath = Join-Path $rootPath $backgroundByRole[$role]
            $background = $layout.Shapes.AddPicture($assetPath, 0, -1, 0, 0, $slideWidth, $slideHeight)
            $background.Name = "background-$role"

            $surfaceRows = [Collections.Generic.List[object]]::new()
            $surfaceIndex = 0
            foreach ($surface in @($slideSpec.surfaces | Where-Object { $null -ne $_ })) {
                $id = if ($surface.id) { [string]$surface.id } else { [string]$surfaceIndex }
                $shapeName = "surface-$id"
                $frame = Convert-Region $surface.region $slideWidth $slideHeight $slideSpec.composition_offset_percent
                $geometry = if ([string]$surface.shape -eq 'rect') { 1 } else { 5 }
                $shape = $layout.Shapes.AddShape($geometry, $frame[0], $frame[1], $frame[2], $frame[3])
                $shape.Name = $shapeName
                $shape.Fill.Visible = -1
                $shape.Fill.ForeColor.RGB = Convert-HexToOfficeRgb ([string]$surface.fill)
                $shape.Fill.Transparency = if ($null -ne $surface.transparency) { [double]$surface.transparency } else { 0 }
                $lineColor = if ($surface.line_fill) { [string]$surface.line_fill } else { '#000000' }
                $shape.Line.Visible = if ($surface.line_fill -and $surface.line_fill -ne 'none') { -1 } else { 0 }
                if ($shape.Line.Visible) {
                    $shape.Line.ForeColor.RGB = Convert-HexToOfficeRgb $lineColor
                    $shape.Line.Weight = if ($null -ne $surface.line_width) { [double]$surface.line_width } else { 0.75 }
                }
                $radiusStagePx = if ($null -ne $surface.corner_radius_stage_px) { [double]$surface.corner_radius_stage_px } else { 18.0 }
                $adjustment = $null
                if ($geometry -eq 5) {
                    $radiusPt = $radiusStagePx * 0.5
                    $shortSidePt = [Math]::Min([double]$shape.Width, [double]$shape.Height)
                    $adjustment = [Math]::Min(0.5, $radiusPt / $shortSidePt)
                    $shape.Adjustments.Item(1) = $adjustment
                }
                $shape.ZOrder(1)
                $surfaceRows.Add([pscustomobject]@{
                    id = $shapeName
                    radius_stage_px = $(if ($geometry -eq 5) { $radiusStagePx } else { $null })
                    radius_pptx_px = $(if ($geometry -eq 5) { $radiusStagePx * (2.0 / 3.0) } else { $null })
                    adjustment = $adjustment
                })
                $surfaceIndex += 1
            }

            foreach ($rule in @($slideSpec.rules | Where-Object { $null -ne $_ })) {
                $frame = Convert-Region $rule.region $slideWidth $slideHeight $slideSpec.composition_offset_percent
                $shape = $layout.Shapes.AddShape(1, $frame[0], $frame[1], $frame[2], [Math]::Max(1.0, $frame[3]))
                $shape.Name = "rule-$($rule.id)"
                $shape.Fill.Visible = -1
                $shape.Fill.ForeColor.RGB = Convert-HexToOfficeRgb ([string]$rule.fill)
                $shape.Line.Visible = 0
            }

            $background.ZOrder(1)
            foreach ($shape in $layout.Shapes) { if ($shape.Type -eq 14) { Set-NoBullet $shape } }
            $layoutRows.Add([pscustomobject]@{
                layout = $layoutName
                background_role = $role
                background_asset = $backgroundByRole[$role].Replace('\', '/')
                composition_offset_percent = $slideSpec.composition_offset_percent
                surfaces = $surfaceRows
                rules = @($slideSpec.rules | Where-Object { $null -ne $_ }).Count
            })
        }

        foreach ($slide in $presentation.Slides) {
            foreach ($shape in $slide.Shapes) { if ($shape.Type -eq 14) { Set-NoBullet $shape } }
        }
        $presentation.Save()
    }
    finally { $presentation.Close() }
}
finally {
    $app.Quit()
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) | Out-Null
}

$relativePptx = [IO.Path]::GetRelativePath($rootPath, $pptxPath).Replace('\', '/')
$relativeSelection = [IO.Path]::GetRelativePath($rootPath, $selectionPath).Replace('\', '/')
$report = [pscustomobject]@{
    status = 'pass'
    artifact = $relativePptx
    selection_manifest = $relativeSelection
    background_set_id = [string]$backgroundSet.background_set_id
    corner_radius_policy = [pscustomobject]@{ mode = 'absolute'; default_stage_px = 18; default_pptx_px = 12 }
    layouts = $layoutRows
}
[IO.File]::WriteAllText($reportFull, ($report | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
Write-Output ($report | ConvertTo-Json -Depth 30 -Compress)
