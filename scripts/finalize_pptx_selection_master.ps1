param(
    [Parameter(Mandatory = $true)]
    [string]$InputPptx,

    [Parameter(Mandatory = $true)]
    [string]$RuntimeManifest,

    [Parameter(Mandatory = $true)]
    [string]$SelectionManifest,

    [Parameter(Mandatory = $true)]
    [string]$OutputPptx,

    [string]$PreviewDir,

    [string]$FinalizationReport
)

# This is the per-page companion to finalize_pptx_background_master.ps1.
# Artifact-tool owns the seed and native chart/table/picture materialization;
# PowerPoint owns the final Master -> Custom Layout -> Slide relationship and
# exact typed Placeholder serialization.
$ErrorActionPreference = 'Stop'

$msoFalse = 0
$msoTrue = -1
$msoSendToBack = 1
$msoPlaceholder = 14
$msoTextOrientationHorizontal = 1
$msoChart = 3
$msoTable = 19
$msoPicture = 13
$ppSaveAsOpenXMLPresentation = 24
$placeholderType = @{
    title = 1
    body = 2
    subtitle = 4
    chart = 8
    table = 12
    picture = 18
}
$nonTextPlaceholderTypes = @('picture', 'chart', 'table')
$alignment = @{ left = 1; center = 2; right = 3 }

function Resolve-AbsolutePath {
    param([string]$Value, [string]$ProjectRoot)
    if ([System.IO.Path]::IsPathRooted($Value)) { return [System.IO.Path]::GetFullPath($Value) }
    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Value))
}

function To-PortablePath {
    param([string]$Value, [string]$ProjectRoot)
    return [System.IO.Path]::GetRelativePath($ProjectRoot, [System.IO.Path]::GetFullPath($Value)).Replace('\', '/')
}

function Convert-HexToOfficeRgb {
    param([string]$Hex)
    $clean = $Hex.TrimStart('#')
    $r = [Convert]::ToInt32($clean.Substring(0, 2), 16)
    $g = [Convert]::ToInt32($clean.Substring(2, 2), 16)
    $b = [Convert]::ToInt32($clean.Substring(4, 2), 16)
    return $r + ($g * 256) + ($b * 65536)
}

function Convert-RegionToPoints {
    param([object[]]$Region, [double]$SlideWidth, [double]$SlideHeight)
    # ConvertFrom-Json can bind a four-value region as one nested Object[];
    # flatten it before arithmetic so COM receives four scalar coordinates.
    $values = @($Region | ForEach-Object {
        if ($_ -is [System.Collections.IEnumerable] -and -not ($_ -is [string])) {
            foreach ($item in $_) { [double]$item }
        }
        else { [double]$_ }
    })
    if ($values.Count -ne 4) { throw "Expected four region values, got $($values.Count)." }
    # Do not use comma-separated arithmetic inside @(...): PowerShell can bind
    # the comma expression as an Object[] divisor. Materialize scalars first.
    $left = ([double]$values[0]) * $SlideWidth / 100.0
    $top = ([double]$values[1]) * $SlideHeight / 100.0
    $width = ([double]$values[2]) * $SlideWidth / 100.0
    $height = ([double]$values[3]) * $SlideHeight / 100.0
    return @(
        $left
        $top
        $width
        $height
    )
}

function Get-SelectionMaster {
    param($Presentation, [string]$FirstLayoutName)
    for ($designIndex = 1; $designIndex -le $Presentation.Designs.Count; $designIndex += 1) {
        $master = $Presentation.Designs.Item($designIndex).SlideMaster
        for ($layoutIndex = 1; $layoutIndex -le $master.CustomLayouts.Count; $layoutIndex += 1) {
            if ([string]$master.CustomLayouts.Item($layoutIndex).Name -eq $FirstLayoutName) {
                return $master
            }
        }
    }
    return $Presentation.SlideMaster
}

function Get-PlaceholderClosestToRegion {
    param($Slide, [int]$Type, [object[]]$Box, [hashtable]$UsedShapeIds)
    $targetX = ([double]$Box[0]) + ([double]$Box[2] / 2.0)
    $targetY = ([double]$Box[1]) + ([double]$Box[3] / 2.0)
    $best = $null
    $bestDistance = [double]::MaxValue
    foreach ($shape in $Slide.Shapes.Placeholders) {
        if ([int]$shape.PlaceholderFormat.Type -ne $Type) { continue }
        if ($UsedShapeIds.ContainsKey([string]$shape.Id)) { continue }
        $shapeX = ([double]$shape.Left) + ([double]$shape.Width / 2.0)
        $shapeY = ([double]$shape.Top) + ([double]$shape.Height / 2.0)
        $distance = [Math]::Pow($shapeX - $targetX, 2) + [Math]::Pow($shapeY - $targetY, 2)
        if ($distance -lt $bestDistance) {
            $best = $shape
            $bestDistance = $distance
        }
    }
    if (-not $best) { throw "Typed Placeholder type $Type was not created near the requested region." }
    return $best
}

function Get-SelectionStyle {
    param($Placeholder)
    $type = [string]$Placeholder.placeholder_type
    $fontSize = if ($Placeholder.font_size_stage_px) { [double]$Placeholder.font_size_stage_px * 0.5 } elseif ($type -eq 'title') { 28.0 } elseif ($type -eq 'subtitle') { 14.0 } else { 12.0 }
    if ([string]$Placeholder.id -like 'stat-*') { $fontSize = 27.0 }
    if ([string]$Placeholder.id -like 'chapter-*') { $fontSize = 14.0 }
    return [pscustomobject]@{
        font_role = if ($type -eq 'title') { 'heading' } else { 'body' }
        color_role = if ($type -eq 'subtitle') { 'secondary_text' } else { 'primary_text' }
        font_size = $fontSize
        bold = ($type -eq 'title' -or [string]$Placeholder.id -like 'stat-*')
        alignment = 'left'
    }
}

function Set-PlaceholderStyle {
    param($Shape, $Style, $Manifest)
    $fontName = [string]$Manifest.fonts.($Style.font_role)
    $color = Convert-HexToOfficeRgb ([string]$Manifest.colors.($Style.color_role))
    $Shape.TextFrame.MarginLeft = 0
    $Shape.TextFrame.MarginRight = 0
    $Shape.TextFrame.MarginTop = 0
    $Shape.TextFrame.MarginBottom = 0
    $Shape.TextFrame.WordWrap = $msoTrue
    try { $Shape.TextFrame.VerticalAnchor = 3 } catch {}
    try { $Shape.TextFrame2.VerticalAnchor = 3 } catch {}
    $range = $Shape.TextFrame.TextRange
    $range.Font.Name = $fontName
    try { $range.Font.NameFarEast = $fontName } catch {}
    $range.Font.Size = [single]$Style.font_size
    $range.Font.Bold = if ($Style.bold) { $msoTrue } else { $msoFalse }
    $range.Font.Color.RGB = $color
    $range.ParagraphFormat.Alignment = $alignment[[string]$Style.alignment]
    $range.ParagraphFormat.Bullet.Visible = $msoFalse
}

function Get-SelectionText {
    param($Payload, [string]$PlaceholderId)
    $property = $Payload.PSObject.Properties[$PlaceholderId]
    if ($property) {
        $value = $property.Value
        if ($value -is [string]) { return [string]$value }
        if ($value -is [System.Collections.IEnumerable]) {
            return (@($value | ForEach-Object { [string]$_ }) -join "`r")
        }
    }
    if ($PlaceholderId -eq 'steps' -and $Payload.steps) {
        return (@($Payload.steps | ForEach-Object { "• $_" }) -join "`r")
    }
    if ($PlaceholderId -eq 'scorecards' -and $Payload.scorecards) {
        return (@($Payload.scorecards | ForEach-Object { "• $_" }) -join "`r")
    }
    return ''
}

function Test-ShapeHasChart {
    param($Shape)
    return [int]$Shape.Type -eq $msoChart
}

function Test-ShapeHasTable {
    param($Shape)
    return [int]$Shape.Type -eq $msoTable
}

function Get-NativeCopyDelayMs {
    param([int]$ShapeType, [int]$Attempt)
    if ($ShapeType -in @($msoChart, $msoTable)) { return @(150, 300, 600)[$Attempt - 1] }
    if ($ShapeType -eq $msoPicture) { return @(100, 200, 400)[$Attempt - 1] }
    return @(75, 150, 300)[$Attempt - 1]
}

function Test-CopiedNativeObject {
    param($Source, $Target)
    if ([int]$Source.Type -ne [int]$Target.Type) { return $false }
    if ([int]$Source.Type -eq $msoChart) { return Test-ShapeHasChart $Target }
    if ([int]$Source.Type -eq $msoTable) { return Test-ShapeHasTable $Target }
    if ([int]$Source.Type -eq $msoPicture) { return [int]$Target.Type -eq $msoPicture }
    return $true
}

function Test-NativeSeedOwnsPlaceholderContent {
    param($Slide, [string]$PlaceholderId)
    $patterns = switch ($PlaceholderId) {
        'steps' { @('process-node-*', 'process-label-*', 'process-body-*', 'process-route') }
        'scorecards' { @('score-label-*', 'score-body-*', 'score-divider-*') }
        default { @() }
    }
    if ($patterns.Count -eq 0) { return $false }
    for ($shapeIndex = 1; $shapeIndex -le $Slide.Shapes.Count; $shapeIndex += 1) {
        $name = [string]$Slide.Shapes.Item($shapeIndex).Name
        foreach ($pattern in $patterns) {
            if ($name -like $pattern) { return $true }
        }
    }
    return $false
}

function Copy-SeedNativeObjects {
    param($SourceSlide, $TargetSlide)
    $copied = @()
    for ($shapeIndex = 1; $shapeIndex -le $SourceSlide.Shapes.Count; $shapeIndex += 1) {
        $source = $SourceSlide.Shapes.Item($shapeIndex)
        if ([int]$source.Type -eq $msoPlaceholder) { continue }
        $expectedType = [int]$source.Type
        $target = $null
        $attemptRecord = @()
        for ($attempt = 1; $attempt -le 3; $attempt += 1) {
            $delay = Get-NativeCopyDelayMs -ShapeType $expectedType -Attempt $attempt
            [void]$source.Copy()
            Start-Sleep -Milliseconds $delay
            $range = $TargetSlide.Shapes.Paste()
            $candidate = $range.Item(1)
            $targetType = [int]$candidate.Type
            $matches = Test-CopiedNativeObject -Source $source -Target $candidate
            $attemptRecord += [pscustomobject]@{ attempt = $attempt; delay_ms = $delay; source_type = $expectedType; target_type = $targetType; match = $matches }
            if ($matches) {
                $target = $candidate
                break
            }
            $candidate.Delete()
            Start-Sleep -Milliseconds 25
        }
        if (-not $target) {
            throw "Native copy failed after 3 attempts: source=$([string]$source.Name) type=$expectedType"
        }
        $copied += [pscustomobject]@{
            type = $expectedType
            name = [string]$target.Name
            left = [double]$target.Left
            top = [double]$target.Top
            width = [double]$target.Width
            height = [double]$target.Height
            has_chart = Test-ShapeHasChart $target
            has_table = Test-ShapeHasTable $target
            attempts = $attemptRecord
        }
    }
    return @($copied)
}

$inputPath = (Resolve-Path -LiteralPath $InputPptx).Path
$manifestPath = (Resolve-Path -LiteralPath $RuntimeManifest).Path
$selectionPath = (Resolve-Path -LiteralPath $SelectionManifest).Path
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$selection = Get-Content -Raw -Encoding UTF8 -LiteralPath $selectionPath | ConvertFrom-Json
if ([string]$manifest.kind -ne 'pptx_background_runtime_manifest') { throw 'Invalid PPTX background runtime manifest kind.' }
if ([string]$selection.kind -ne 'shared_cold_chain_pptx_selection') { throw 'Invalid per-page PPTX selection manifest kind.' }
if (@($selection.slides).Count -ne 10) { throw 'Per-page PPTX selection must contain exactly ten slides.' }
if (-not $manifest.fonts.heading -or -not $manifest.fonts.body -or -not $manifest.colors.primary_text -or -not $manifest.colors.secondary_text) {
    throw 'Selection finalizer runtime manifest is missing fonts or text colors.'
}
$requiredRoles = @('cover', 'toc', 'content-a', 'content-b', 'content-c', 'qa')
$roleById = @{}
foreach ($role in @($manifest.roles)) { $roleById[[string]$role.id] = $role }
if (@($requiredRoles | Where-Object { -not $roleById.ContainsKey($_) }).Count -gt 0) { throw 'Runtime manifest must contain all six background roles.' }
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $manifestPath) '..\..\..'))
$outputPath = [System.IO.Path]::GetFullPath($OutputPptx)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null

$powerPoint = $null
$presentation = $null
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($inputPath, $msoFalse, $msoFalse, $msoFalse)
    $slideWidth = [double]$presentation.PageSetup.SlideWidth
    $slideHeight = [double]$presentation.PageSetup.SlideHeight
    $sourceSlideCount = $presentation.Slides.Count
    if ($sourceSlideCount -lt @($selection.slides).Count) { throw 'Artifact-tool seed has fewer slides than the typed selection plan.' }
    $master = Get-SelectionMaster -Presentation $presentation -FirstLayoutName ([string]$selection.slides[0].layout_name)
    $createdLayouts = @{}
    $records = @()
    foreach ($page in @($selection.slides)) {
        $tempLayoutName = "{0}--native-finalizer" -f [string]$page.layout_name
        $layout = $master.CustomLayouts.Add($master.CustomLayouts.Count + 1)
        $layout.Name = $tempLayoutName
        for ($shapeIndex = $layout.Shapes.Count; $shapeIndex -ge 1; $shapeIndex -= 1) { $layout.Shapes.Item($shapeIndex).Delete() }
        $role = $roleById[[string]$page.background_role]
        $assetPath = Resolve-AbsolutePath ([string]$role.asset) $projectRoot
        if (-not (Test-Path -LiteralPath $assetPath)) { throw "Missing background asset: $assetPath" }
        $background = $layout.Shapes.AddPicture($assetPath, $msoFalse, $msoTrue, 0, 0, $slideWidth, $slideHeight)
        $background.Name = "__PPTX_BG__$([string]$page.background_role)"
        $background.LockAspectRatio = $msoFalse
        $background.ZOrder($msoSendToBack)
        $placeholderRecords = @()
        $layoutTypeCounts = @{}
        foreach ($placeholder in @($page.placeholder_schema)) {
            $typeName = [string]$placeholder.placeholder_type
            $type = $placeholderType[$typeName]
            if (-not $type) { throw "Unsupported typed Placeholder: $typeName" }
            $box = Convert-RegionToPoints -Region @($placeholder.region) -SlideWidth $slideWidth -SlideHeight $slideHeight
            $count = if ($layoutTypeCounts.ContainsKey($typeName)) { [int]$layoutTypeCounts[$typeName] } else { 0 }
            # PowerPoint only permits one ppPlaceholderTitle and one
            # ppPlaceholderSubtitle on a CustomLayout. Keep the first typed
            # slot in the Layout; later subtitle semantics remain real native
            # slide text at the same schema geometry, never a fake body slot.
            if ($typeName -in @('title', 'subtitle') -and $count -ge 1) {
                $placeholderRecords += [pscustomobject]@{
                    id = [string]$placeholder.id
                    type = $typeName
                    index = $null
                    region = @($placeholder.region)
                    materialization = 'native-text-powerpoint-api-limit'
                }
                continue
            }
            $shape = $layout.Shapes.AddPlaceholder($type, $box[0], $box[1], $box[2], $box[3])
            $layoutTypeCounts[$typeName] = $count + 1
            $shape.Name = "ph--$([string]$page.slide_id)--$([string]$placeholder.id)"
            if ($nonTextPlaceholderTypes -notcontains $typeName) {
                $shape.TextFrame.TextRange.Text = ''
                Set-PlaceholderStyle -Shape $shape -Style (Get-SelectionStyle $placeholder) -Manifest $manifest
            }
            $placeholderRecords += [pscustomobject]@{
                id = [string]$placeholder.id
                type = $typeName
                index = [int]$shape.PlaceholderFormat.Index
                region = @($placeholder.region)
                materialization = 'placeholder'
            }
        }
        $createdLayouts[[string]$page.slide_id] = $layout
        $records += [pscustomobject]@{ slide_id = [string]$page.slide_id; layout_name = [string]$page.layout_name; background_role = [string]$page.background_role; layout_placeholders = $placeholderRecords }
    }

    for ($pageIndex = 0; $pageIndex -lt @($selection.slides).Count; $pageIndex += 1) {
        $page = $selection.slides[$pageIndex]
        $layout = $createdLayouts[[string]$page.slide_id]
        # New slides append after every seed slide, so this remains the source
        # page until the final deletion pass.
        $seedSlide = $presentation.Slides.Item($pageIndex + 1)
        $slide = $presentation.Slides.AddSlide($presentation.Slides.Count + 1, $layout)
        $slide.Name = "slide--$([string]$page.slide_id)"
        $used = @{}
        $slidePlaceholderRecords = @()
        $layoutRecordsById = @{}
        foreach ($layoutRecord in @($records[$pageIndex].layout_placeholders)) { $layoutRecordsById[[string]$layoutRecord.id] = $layoutRecord }
        foreach ($placeholder in @($page.placeholder_schema)) {
            $typeName = [string]$placeholder.placeholder_type
            $type = $placeholderType[$typeName]
            $box = Convert-RegionToPoints -Region @($placeholder.region) -SlideWidth $slideWidth -SlideHeight $slideHeight
            $layoutRecord = $layoutRecordsById[[string]$placeholder.id]
            if ([string]$layoutRecord.materialization -eq 'native-text-powerpoint-api-limit') {
                $shape = $slide.Shapes.AddTextbox($msoTextOrientationHorizontal, $box[0], $box[1], $box[2], $box[3])
                $shape.Name = "native--$([string]$page.slide_id)--$([string]$placeholder.id)"
                $shape.TextFrame.TextRange.Text = Get-SelectionText -Payload $page.payload -PlaceholderId ([string]$placeholder.id)
                Set-PlaceholderStyle -Shape $shape -Style (Get-SelectionStyle $placeholder) -Manifest $manifest
                $slidePlaceholderRecords += [pscustomobject]@{ id = [string]$placeholder.id; type = $typeName; index = $null; region = @($placeholder.region); materialization = 'native-text-powerpoint-api-limit' }
                continue
            }
            $shape = Get-PlaceholderClosestToRegion -Slide $slide -Type $type -Box $box -UsedShapeIds $used
            $used[[string]$shape.Id] = $true
            $shape.Name = "ph--$([string]$page.slide_id)--$([string]$placeholder.id)"
            $contentOwner = 'placeholder-text'
            if ($nonTextPlaceholderTypes -notcontains $typeName) {
                if (Test-NativeSeedOwnsPlaceholderContent -Slide $seedSlide -PlaceholderId ([string]$placeholder.id)) {
                    # A process/scorecard semantic group has already been
                    # materialized as individual native objects in the seed.
                    # Do not duplicate its visible copy into a generic body
                    # Placeholder; keep that Placeholder empty and record the
                    # native child ownership below.
                    $shape.TextFrame.TextRange.Text = ''
                    $contentOwner = 'native-seed-children'
                }
                else {
                    $shape.TextFrame.TextRange.Text = Get-SelectionText -Payload $page.payload -PlaceholderId ([string]$placeholder.id)
                }
                Set-PlaceholderStyle -Shape $shape -Style (Get-SelectionStyle $placeholder) -Manifest $manifest
            }
            $slidePlaceholderRecords += [pscustomobject]@{ id = [string]$placeholder.id; type = $typeName; index = [int]$shape.PlaceholderFormat.Index; region = @($placeholder.region); materialization = 'placeholder'; content_owner = $contentOwner }
        }
        $copied = Copy-SeedNativeObjects -SourceSlide $seedSlide -TargetSlide $slide
        $records[$pageIndex] | Add-Member -NotePropertyName slide_placeholders -NotePropertyValue $slidePlaceholderRecords
        $records[$pageIndex] | Add-Member -NotePropertyName copied_native_objects -NotePropertyValue $copied
    }

    for ($index = @($selection.slides).Count; $index -ge 1; $index -= 1) { $presentation.Slides.Item($index).Delete() }
    $oldLayoutNames = @($selection.slides | ForEach-Object { [string]$_.layout_name })
    for ($layoutIndex = $master.CustomLayouts.Count; $layoutIndex -ge 1; $layoutIndex -= 1) {
        $layout = $master.CustomLayouts.Item($layoutIndex)
        if ($oldLayoutNames -contains [string]$layout.Name) { $layout.Delete() }
    }
    foreach ($page in @($selection.slides)) { $createdLayouts[[string]$page.slide_id].Name = [string]$page.layout_name }

    $presentation.SaveAs($outputPath, $ppSaveAsOpenXMLPresentation)
    if ($PreviewDir) {
        $previewPath = [System.IO.Path]::GetFullPath($PreviewDir)
        New-Item -ItemType Directory -Force -Path $previewPath | Out-Null
        $presentation.Export($previewPath, 'PNG', 1600, 900)
    }
    $result = [pscustomobject]@{
        schema_version = 1
        kind = 'pptx_selection_powerpoint_finalization'
        pass = $true
        output = To-PortablePath -Value $outputPath -ProjectRoot $projectRoot
        selection_manifest = To-PortablePath -Value $selectionPath -ProjectRoot $projectRoot
        runtime_manifest = To-PortablePath -Value $manifestPath -ProjectRoot $projectRoot
        master = [string]$master.Name
        reset_policy = 'layout-authoritative'
        slides = $records
    }
    if ($FinalizationReport) {
        $reportPath = [System.IO.Path]::GetFullPath($FinalizationReport)
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
        $result | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 -LiteralPath $reportPath
    }
    $result | ConvertTo-Json -Depth 6 -Compress
}
finally {
    if ($presentation) { try { $presentation.Close() } catch {}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    if ($powerPoint) { try { $powerPoint.Quit() } catch {}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
