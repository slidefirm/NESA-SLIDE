param(
    [Parameter(Mandatory = $true)]
    [string]$InputPptx,

    [Parameter(Mandatory = $true)]
    [string]$RuntimeManifest,

    [Parameter(Mandatory = $true)]
    [string]$OutputPptx,

    [string]$PreviewDir,

    [string]$DemoContent = 'prompt_system/pptx_background_sets/brand-editorial-demo-content.json'
)

$ErrorActionPreference = 'Stop'

$msoFalse = 0
$msoTrue = -1
$msoSendToBack = 1
$msoShapeRectangle = 1
$msoShapeRoundedRectangle = 5
$ppSaveAsOpenXMLPresentation = 24

$placeholderType = @{
    title = 1
    body = 2
    subtitle = 4
    picture = 18
    chart = 8
    table = 12
}
$nonTextPlaceholderTypes = @('picture', 'chart', 'table')

$alignment = @{
    left = 1
    center = 2
    right = 3
}

function Resolve-AbsolutePath {
    param(
        [string]$Value,
        [string]$ProjectRoot
    )
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Value))
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
    param(
        [object[]]$Region,
        [double]$SlideWidth,
        [double]$SlideHeight
    )
    $left = ([double]$Region[0]) * ([double]$SlideWidth) / 100.0
    $top = ([double]$Region[1]) * ([double]$SlideHeight) / 100.0
    $width = ([double]$Region[2]) * ([double]$SlideWidth) / 100.0
    $height = ([double]$Region[3]) * ([double]$SlideHeight) / 100.0
    return @($left; $top; $width; $height)
}

function Add-LayoutSurfaces {
    param(
        $Layout,
        $Role,
        [double]$SlideWidth,
        [double]$SlideHeight
    )
    if ($null -eq $Role.surfaces) {
        return
    }
    foreach ($surface in @($Role.surfaces)) {
        $region = $surface.region
        if (-not ($region -is [System.Array]) -or $region.Count -ne 4) {
            throw "Surface $($Role.id).$($surface.id) must declare a four-value region."
        }
        $box = Convert-RegionToPoints -Region @($region) -SlideWidth $SlideWidth -SlideHeight $SlideHeight
        $geometry = [string]$surface.shape
        $shapeType = if ($geometry -in @('roundRect', 'rounded-rectangle')) { $msoShapeRoundedRectangle } else { $msoShapeRectangle }
        $shape = $Layout.Shapes.AddShape($shapeType, $box[0], $box[1], $box[2], $box[3])
        $shape.Name = "surface--$($Role.id)--$($surface.id)"
        $fillHex = [string]$surface.fill
        if ([string]::IsNullOrWhiteSpace($fillHex)) { $fillHex = '#000000' }
        $shape.Fill.ForeColor.RGB = Convert-HexToOfficeRgb $fillHex
        $transparency = if ($null -ne $surface.transparency) { [double]$surface.transparency } else { 0.0 }
        $shape.Fill.Transparency = [single][Math]::Max(0.0, [Math]::Min(1.0, $transparency))
        $shape.Line.Visible = $msoFalse
        if (-not [string]::IsNullOrWhiteSpace([string]$surface.line_fill)) {
            $shape.Line.Visible = $msoTrue
            $shape.Line.ForeColor.RGB = Convert-HexToOfficeRgb ([string]$surface.line_fill)
            if ($null -ne $surface.line_width) { $shape.Line.Weight = [single]$surface.line_width }
        }
        # Added after the raster background and before placeholders: editable
        # middle layer, with content still above it.
    }
}

function Set-PlaceholderStyle {
    param(
        $Shape,
        $Style,
        $Manifest
    )
    $fontName = [string]$Manifest.fonts.($Style.font_role)
    $fontColor = Convert-HexToOfficeRgb ([string]$Manifest.colors.($Style.color_role))
    $Shape.TextFrame.MarginLeft = 0
    $Shape.TextFrame.MarginRight = 0
    $Shape.TextFrame.MarginTop = 0
    $Shape.TextFrame.MarginBottom = 0
    $Shape.TextFrame.WordWrap = $msoTrue
    # Make the default vertical anchor explicit on both PowerPoint text engines.
    try { $Shape.TextFrame.VerticalAnchor = 3 } catch {}
    try { $Shape.TextFrame2.VerticalAnchor = 3 } catch {}
    $range = $Shape.TextFrame.TextRange
    $range.Font.Name = $fontName
    try { $range.Font.NameFarEast = $fontName } catch {}
    $range.Font.Size = [single]$Style.font_size
    $range.Font.Bold = if ($Style.bold) { $msoTrue } else { $msoFalse }
    $range.Font.Color.RGB = $fontColor
    $range.ParagraphFormat.Alignment = $alignment[[string]$Style.alignment]
    $range.ParagraphFormat.SpaceWithin = 1.0
    $range.ParagraphFormat.Bullet.Visible = $msoFalse
}

function Set-SemanticLineBreak {
    param(
        $Shape,
        [string]$Text,
        [double]$MaximumWidth,
        [bool]$AllowEnumerationComma = $false
    )

    if ([string]::IsNullOrWhiteSpace($Text) -or
        $Text.Contains("`r") -or
        $Text.Contains("`n") -or
        $Text.Contains([string][char]11)) {
        return $false
    }

    $naturalLineCount = 1
    try { $naturalLineCount = [int]$Shape.TextFrame.TextRange.Lines().Count } catch {}
    $originalWidth = [double]$Shape.Width
    $originalHeight = [double]$Shape.Height
    $measurementWidth = [Math]::Max($MaximumWidth * 3.0, 1440.0)
    $Shape.Width = [single]$measurementWidth
    $Shape.TextFrame.WordWrap = $msoFalse
    $singleLineWidth = [double]$Shape.TextFrame2.TextRange.BoundWidth
    $Shape.Width = [single]$originalWidth
    $Shape.Height = [single]$originalHeight
    $Shape.TextFrame.WordWrap = $msoTrue
    Write-Verbose ("Semantic break measure: '{0}' lines={1} single={2:N1} max={3:N1}" -f $Text, $naturalLineCount, $singleLineWidth, $MaximumWidth)
    if ($naturalLineCount -le 1 -and $singleLineWidth -le ($MaximumWidth + 1.5)) {
        return $false
    }

    $candidates = @()
    $semanticPunctuation = @(
        0xFF0C, # fullwidth comma
        0xFF1B, # fullwidth semicolon
        0xFF1A, # fullwidth colon
        0xFF01, # fullwidth exclamation mark
        0xFF1F, # fullwidth question mark
        0x3002, # ideographic full stop
        0x002C, # comma
        0x003B, # semicolon
        0x003A, # colon
        0x0021, # exclamation mark
        0x003F  # question mark
    )
    if ($AllowEnumerationComma) {
        $semanticPunctuation += 0x3001 # ideographic comma, title only
    }
    for ($index = 0; $index -lt $Text.Length; $index += 1) {
        if ($semanticPunctuation -notcontains [int][char]$Text[$index]) {
            continue
        }
        $split = $index + 1
        $ratio = [double]$split / [double]$Text.Length
        if ($ratio -lt 0.34 -or $ratio -gt 0.66) {
            continue
        }
        $left = $Text.Substring(0, $split).TrimEnd()
        $right = $Text.Substring($split).TrimStart()
        if ($left.Length -lt 3 -or $right.Length -lt 3) {
            continue
        }
        $candidates += [pscustomobject]@{
            split = $split
            score = [Math]::Abs(0.5 - $ratio)
            left = $left
            right = $right
        }
    }

    Write-Verbose ("Semantic break candidates: '{0}' count={1}" -f $Text, $candidates.Count)
    if ($candidates.Count -eq 0) {
        return $false
    }

    foreach ($candidate in @($candidates | Sort-Object score)) {
        $candidateText = $candidate.left + [char]11 + $candidate.right
        $Shape.TextFrame.TextRange.Text = $candidateText
        $Shape.Width = [single]$measurementWidth
        $Shape.TextFrame.WordWrap = $msoFalse
        $candidateWidth = [double]$Shape.TextFrame2.TextRange.BoundWidth
        $Shape.Width = [single]$originalWidth
        $Shape.Height = [single]$originalHeight
        $Shape.TextFrame.WordWrap = $msoTrue
        Write-Verbose ("Semantic break candidate: '{0}' width={1:N1}" -f $candidateText, $candidateWidth)
        if ($candidateWidth -le ($MaximumWidth + 1.5)) {
            return $true
        }
    }

    $Shape.TextFrame.TextRange.Text = $Text
    $Shape.TextFrame.WordWrap = $msoTrue
    return $false
}

function Set-MetricTextStyle {
    param(
        $Shape,
        $Manifest
    )
    $range = $Shape.TextFrame.TextRange
    $range.ParagraphFormat.SpaceWithin = 1.0
    $range.ParagraphFormat.SpaceBefore = 0
    $range.ParagraphFormat.SpaceAfter = 0
    $headingFont = [string]$Manifest.fonts.heading
    $bodyFont = [string]$Manifest.fonts.body
    $accent = Convert-HexToOfficeRgb ([string]$Manifest.colors.accent)
    $primary = Convert-HexToOfficeRgb ([string]$Manifest.colors.primary_text)
    $secondary = Convert-HexToOfficeRgb ([string]$Manifest.colors.secondary_text)

    if ($range.Paragraphs().Count -ge 1) {
        $number = $range.Paragraphs(1, 1)
        $number.Font.Name = $headingFont
        try { $number.Font.NameFarEast = $headingFont } catch {}
        $number.Font.Size = 44
        $number.Font.Bold = $msoTrue
        $number.Font.Color.RGB = $accent
    }
    if ($range.Paragraphs().Count -ge 2) {
        $title = $range.Paragraphs(2, 1)
        $title.Font.Name = $headingFont
        try { $title.Font.NameFarEast = $headingFont } catch {}
        $title.Font.Size = 28
        $title.Font.Bold = $msoTrue
        $title.Font.Color.RGB = $primary
    }
    if ($range.Paragraphs().Count -ge 3) {
        $body = $range.Paragraphs(3, $range.Paragraphs().Count - 2)
        $body.Font.Name = $bodyFont
        try { $body.Font.NameFarEast = $bodyFont } catch {}
        $body.Font.Size = 16
        $body.Font.Bold = $msoFalse
        $body.Font.Color.RGB = $secondary
    }
}

function Fit-ShapeToTextBounds {
    param(
        $Shape,
        [double]$MaximumWidth,
        [double]$MaximumHeight
    )
    $Shape.TextFrame.WordWrap = $msoTrue
    $Shape.TextFrame.MarginLeft = 0
    $Shape.TextFrame.MarginRight = 0
    $Shape.TextFrame.MarginTop = 0
    $Shape.TextFrame.MarginBottom = 0
    try { $Shape.TextFrame.VerticalAnchor = 1 } catch {}

    for ($iteration = 0; $iteration -lt 3; $iteration += 1) {
        $boundWidth = [double]$Shape.TextFrame2.TextRange.BoundWidth
        $boundHeight = [double]$Shape.TextFrame2.TextRange.BoundHeight
        $minimumHeight = [double]$Shape.TextFrame.TextRange.Font.Size * 1.15
        $targetWidth = [Math]::Min($MaximumWidth, [Math]::Max(12.0, $boundWidth + 6.0))
        $targetHeight = [Math]::Min($MaximumHeight, [Math]::Max($minimumHeight, $boundHeight + 4.0))
        $Shape.Width = [single]$targetWidth
        $Shape.Height = [single]$targetHeight
    }
}

function Get-PlaceholderClosestToRegion {
    param(
        $Slide,
        [int]$Type,
        [object[]]$Box,
        [hashtable]$UsedShapeIds
    )
    $targetX = ([double]$Box[0]) + ([double]$Box[2] / 2.0)
    $targetY = ([double]$Box[1]) + ([double]$Box[3] / 2.0)
    $best = $null
    $bestDistance = [double]::MaxValue
    foreach ($shape in $Slide.Shapes.Placeholders) {
        if ([int]$shape.PlaceholderFormat.Type -ne $Type) {
            continue
        }
        if ($UsedShapeIds.ContainsKey([string]$shape.Id)) {
            continue
        }
        $shapeX = ([double]$shape.Left) + ([double]$shape.Width / 2.0)
        $shapeY = ([double]$shape.Top) + ([double]$shape.Height / 2.0)
        $distance = [Math]::Pow($shapeX - $targetX, 2) + [Math]::Pow($shapeY - $targetY, 2)
        if ($distance -lt $bestDistance) {
            $best = $shape
            $bestDistance = $distance
        }
    }
    if (-not $best) {
        throw "Slide placeholder type $Type near the requested region was not created."
    }
    return $best
}

function Reflow-ContentGroups {
    param(
        $Slide,
        $Role,
        [double]$SlideWidth,
        [double]$SlideHeight,
        $Manifest
    )
    # Layout geometry is authoritative by default. Slide-level text fitting
    # changes x/y/w/h and is discarded by PowerPoint Reset, which makes the
    # default state drift. Legacy reflow is an explicit opt-in only.
    if ([string]$Manifest.reset_policy -ne 'legacy-reflow') {
        return
    }
    if (-not $Role.content_groups) {
        return
    }
    foreach ($group in $Role.content_groups) {
        $fixedFrameMembers = @(
            foreach ($member in @($group.members)) {
                $memberSpec = @($Role.placeholders | Where-Object { [string]$_.name -eq [string]$member }) | Select-Object -First 1
                if ($memberSpec -and (
                    [string]$memberSpec.frame_policy -eq 'fixed' -or
                    [string]$memberSpec.type -in @('title', 'subtitle')
                )) {
                    $member
                }
            }
        )
        # A fixed title/subtitle frame belongs to the selected Layout/Variant.
        # Do not resize, reposition, scale, or rewrap any content group that
        # contains one; old manifests without frame_policy retain legacy behavior.
        if ($fixedFrameMembers.Count -gt 0) {
            continue
        }
        if ([string]$group.vertical_gravity -ne 'center') {
            continue
        }
        $groupBox = Convert-RegionToPoints -Region @($group.region) -SlideWidth $SlideWidth -SlideHeight $SlideHeight
        $shapes = @()
        # Content groups are text-reflow groups. A typed picture/chart/table
        # may share a source group, but must never enter TextFrame measurement
        # or semantic line-break logic; retain only the text members and
        # redistribute the declared total gap across the remaining members.
        $members = @(
            foreach ($member in @($group.members)) {
                $memberSpec = @($Role.placeholders | Where-Object { [string]$_.name -eq [string]$member }) | Select-Object -First 1
                if ($memberSpec -and $nonTextPlaceholderTypes -contains ([string]$memberSpec.type)) {
                    continue
                }
                $member
            }
        )
        if ($members.Count -eq 0) {
            continue
        }
        foreach ($member in $members) {
            $shapeName = "ph--$($Role.id)--$member"
            try {
                $shape = $Slide.Shapes.Item($shapeName)
            }
            catch {
                throw "Content group member not found: $shapeName"
            }
            $shape.Left = [single]$groupBox[0]
            Fit-ShapeToTextBounds -Shape $shape -MaximumWidth ([double]$groupBox[2]) -MaximumHeight ([double]$groupBox[3])
            $shapes += $shape
        }

        $gaps = @()
        foreach ($gapPct in $group.gaps_pct) {
            $gaps += ([double]$gapPct * $SlideHeight / 100.0)
        }
        if ($members.Count -gt 1) {
            $gapTotal = if ($gaps.Count -gt 0) { ($gaps | Measure-Object -Sum).Sum } else { 0.0 }
            $gaps = @(1..($members.Count - 1) | ForEach-Object { [double]$gapTotal / [double]($members.Count - 1) })
        }
        else {
            $gaps = @()
        }

        $shapeHeight = ($shapes | ForEach-Object { [double]$_.Height } | Measure-Object -Sum).Sum
        $gapHeight = if ($gaps.Count -gt 0) { ($gaps | Measure-Object -Sum).Sum } else { 0.0 }
        $utilization = ([double]$shapeHeight + [double]$gapHeight) / [double]$groupBox[3]
        $containsMetric = ($members | Where-Object { [string]$_ -like 'metric-*' }).Count -gt 0
        $scale = 1.0
        if (-not $containsMetric -and $utilization -lt 0.42) {
            $scale = [Math]::Min(1.18, [Math]::Sqrt(0.42 / [Math]::Max(0.10, $utilization)))
            foreach ($shape in $shapes) {
                $shape.TextFrame.TextRange.Font.Size = [single]([double]$shape.TextFrame.TextRange.Font.Size * $scale)
                Fit-ShapeToTextBounds -Shape $shape -MaximumWidth ([double]$groupBox[2]) -MaximumHeight ([double]$groupBox[3])
            }
        }

        # Sparse groups are enlarged only after the first semantic-break pass.
        # Re-evaluate title/subtitle wrapping at the final font size so a new
        # natural wrap cannot split a phrase at an arbitrary character.
        for ($memberIndex = 0; $memberIndex -lt $members.Count; $memberIndex += 1) {
            $memberName = [string]$members[$memberIndex]
            $placeholderSpec = @($Role.placeholders | Where-Object { [string]$_.name -eq $memberName }) | Select-Object -First 1
            if (-not $placeholderSpec) {
                continue
            }
            $styleName = [string]$placeholderSpec.style
            if ($styleName -notin @('title', 'subtitle')) {
                continue
            }
            $shape = $shapes[$memberIndex]
            $currentText = [string]$shape.TextFrame.TextRange.Text
            $placeholderBox = Convert-RegionToPoints -Region @($placeholderSpec.region) -SlideWidth $SlideWidth -SlideHeight $SlideHeight
            $semanticBreakApplied = Set-SemanticLineBreak -Shape $shape -Text $currentText -MaximumWidth ([double]$placeholderBox[2]) -AllowEnumerationComma ($styleName -eq 'title')
            if ($semanticBreakApplied) {
                $style = $Manifest.placeholder_styles.($styleName)
                Set-PlaceholderStyle $shape $style $Manifest
                if ($scale -gt 1.0) {
                    $shape.TextFrame.TextRange.Font.Size = [single]([double]$shape.TextFrame.TextRange.Font.Size * $scale)
                }
                Fit-ShapeToTextBounds -Shape $shape -MaximumWidth ([double]$groupBox[2]) -MaximumHeight ([double]$groupBox[3])
            }
        }

        $totalHeight = 0.0
        foreach ($shape in $shapes) {
            $totalHeight += [double]$shape.Height
        }
        foreach ($gap in $gaps) {
            $totalHeight += [double]$gap
        }
        if ($totalHeight -gt [double]$groupBox[3]) {
            $availableForGaps = [Math]::Max(0.0, [double]$groupBox[3] - ($totalHeight - ($gaps | Measure-Object -Sum).Sum))
            if ($gaps.Count -gt 0) {
                $gaps = @(1..$gaps.Count | ForEach-Object { $availableForGaps / $gaps.Count })
            }
            $totalHeight = [double]$groupBox[3]
        }
        $cursor = [double]$groupBox[1] + (([double]$groupBox[3] - $totalHeight) / 2.0)
        for ($index = 0; $index -lt $shapes.Count; $index += 1) {
            $shapes[$index].Top = [single]$cursor
            $cursor += [double]$shapes[$index].Height
            if ($index -lt $gaps.Count) {
                $cursor += [double]$gaps[$index]
            }
        }
    }
}

$inputPath = (Resolve-Path -LiteralPath $InputPptx).Path
$manifestPath = (Resolve-Path -LiteralPath $RuntimeManifest).Path
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$requiredBackgroundRoles = @('cover', 'toc', 'content-a', 'content-b', 'content-c', 'qa')
if ([string]$manifest.kind -ne 'pptx_background_runtime_manifest') {
    throw "Invalid PPTX background runtime manifest kind."
}
$setThemeId = if ($manifest.background_set_theme_id) { [string]$manifest.background_set_theme_id } else { [string]$manifest.theme_id }
if (-not $manifest.theme_id -or $setThemeId -ne [string]$manifest.theme_id) {
    throw "Background set theme mismatch: set=$setThemeId manifest=$($manifest.theme_id)"
}
$roleIds = @($manifest.roles | ForEach-Object { [string]$_.id })
if ($roleIds.Count -ne $requiredBackgroundRoles.Count -or @($requiredBackgroundRoles | Where-Object { $roleIds -notcontains $_ }).Count -gt 0) {
    throw "PPTX background runtime manifest must contain exactly six roles: $($requiredBackgroundRoles -join ', ')"
}
if (-not $manifest.background_set_id) { Add-Member -InputObject $manifest -NotePropertyName background_set_id -NotePropertyValue ([string]$manifest.theme_id) }
if (-not $manifest.selection_basis) { Add-Member -InputObject $manifest -NotePropertyName selection_basis -NotePropertyValue 'explicit-runtime-manifest' }
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $manifestPath) '..\..\..'))
$demoContentPath = Resolve-AbsolutePath $DemoContent $projectRoot
$demoText = Get-Content -Raw -Encoding UTF8 -LiteralPath $demoContentPath | ConvertFrom-Json
$outputPath = [System.IO.Path]::GetFullPath($OutputPptx)
$outputParent = Split-Path -Parent $outputPath
New-Item -ItemType Directory -Force -Path $outputParent | Out-Null

$powerPoint = $null
$presentation = $null

try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($inputPath, $msoFalse, $msoFalse, $msoFalse)
    $slideWidth = [double]$presentation.PageSetup.SlideWidth
    $slideHeight = [double]$presentation.PageSetup.SlideHeight

    for ($i = $presentation.Slides.Count; $i -ge 1; $i -= 1) {
        $presentation.Slides.Item($i).Delete()
    }

    for ($i = $presentation.SlideMaster.CustomLayouts.Count; $i -ge 1; $i -= 1) {
        $existingLayout = $presentation.SlideMaster.CustomLayouts.Item($i)
        if ($existingLayout.Name -like 'layout--*') {
            $existingLayout.Delete()
        }
    }

    $createdLayouts = @{}
    $semanticBreaks = @()
    foreach ($role in $manifest.roles) {
        $layoutIndex = $presentation.SlideMaster.CustomLayouts.Count + 1
        $layout = $presentation.SlideMaster.CustomLayouts.Add($layoutIndex)
        $layout.Name = "layout--$($role.id)"

        for ($shapeIndex = $layout.Shapes.Count; $shapeIndex -ge 1; $shapeIndex -= 1) {
            $layout.Shapes.Item($shapeIndex).Delete()
        }

        $assetPath = Resolve-AbsolutePath ([string]$role.asset) $projectRoot
        if (-not (Test-Path -LiteralPath $assetPath)) {
            throw "Missing background asset: $assetPath"
        }
        $background = $layout.Shapes.AddPicture(
            $assetPath,
            $msoFalse,
            $msoTrue,
            0,
            0,
            $slideWidth,
            $slideHeight
        )
        $background.Name = "__PPTX_BG__$($role.id)"
        $background.LockAspectRatio = $msoFalse
        $background.ZOrder($msoSendToBack)

        Add-LayoutSurfaces -Layout $layout -Role $role -SlideWidth $slideWidth -SlideHeight $slideHeight

        foreach ($placeholder in $role.placeholders) {
            $type = $placeholderType[[string]$placeholder.type]
            if (-not $type) {
                throw "Unsupported placeholder type: $($placeholder.type)"
            }
            $box = Convert-RegionToPoints -Region @($placeholder.region) -SlideWidth $slideWidth -SlideHeight $slideHeight
            $shape = $layout.Shapes.AddPlaceholder($type, $box[0], $box[1], $box[2], $box[3])
            $shape.Name = "ph--$($role.id)--$($placeholder.name)"
            if ($nonTextPlaceholderTypes -contains ([string]$placeholder.type)) {
                continue
            }
            # Keep Layout placeholders empty. Seed labels such as [title] or
            # [metric-1] leak into the slide when PowerPoint Reset restores
            # Layout inheritance instead of the populated Slide placeholder.
            $shape.TextFrame.TextRange.Text = ''
            $style = $manifest.placeholder_styles.($placeholder.style)
            Set-PlaceholderStyle $shape $style $manifest
        }
        $createdLayouts[[string]$role.id] = $layout
    }

    # The artifact-tool seed carries one generic layout. Once all formal layouts
    # exist, remove every unused seed layout so the delivered master exposes only
    # the six renderer roles defined by the runtime manifest.
    for ($i = $presentation.SlideMaster.CustomLayouts.Count; $i -ge 1; $i -= 1) {
        $existingLayout = $presentation.SlideMaster.CustomLayouts.Item($i)
        if ($existingLayout.Name -notlike 'layout--*') {
            $existingLayout.Delete()
        }
    }

    foreach ($role in $manifest.roles) {
        $layout = $createdLayouts[[string]$role.id]
        $slide = $presentation.Slides.AddSlide($presentation.Slides.Count + 1, $layout)
        $slide.Name = "demo--$($role.id)"
        $usedShapeIds = @{}

        foreach ($placeholder in $role.placeholders) {
            $typeName = [string]$placeholder.type
            $box = Convert-RegionToPoints -Region @($placeholder.region) -SlideWidth $slideWidth -SlideHeight $slideHeight
            $shape = Get-PlaceholderClosestToRegion -Slide $slide -Type $placeholderType[$typeName] -Box $box -UsedShapeIds $usedShapeIds
            $usedShapeIds[[string]$shape.Id] = $true
            $shape.Name = "ph--$($role.id)--$($placeholder.name)"
            if ($nonTextPlaceholderTypes -contains $typeName) {
                continue
            }
            $roleContent = $demoText.([string]$role.id)
            $contentValue = [string]$roleContent.([string]$placeholder.name)
            $contentValue = $contentValue.Replace("`r`n", "`r").Replace("`n", "`r")
            $shape.TextFrame.TextRange.Text = $contentValue
            $styleName = [string]$placeholder.style
            $style = $manifest.placeholder_styles.($styleName)
            Set-PlaceholderStyle $shape $style $manifest
            if ($styleName -in @('title', 'subtitle')) {
                $semanticBreakApplied = Set-SemanticLineBreak -Shape $shape -Text $contentValue -MaximumWidth ([double]$box[2]) -AllowEnumerationComma ($styleName -eq 'title')
                if ($semanticBreakApplied) {
                    $semanticBreaks += "$( [string]$role.id ).$( [string]$placeholder.name )"
                }
                Set-PlaceholderStyle $shape $style $manifest
            }
            if ($styleName -eq 'metric' -and [string]$manifest.reset_policy -eq 'legacy-reflow') {
                Set-MetricTextStyle -Shape $shape -Manifest $manifest
            }
        }
        Reflow-ContentGroups -Slide $slide -Role $role -SlideWidth $slideWidth -SlideHeight $slideHeight -Manifest $manifest
        foreach ($placeholder in $role.placeholders) {
            $styleName = [string]$placeholder.style
            if ($styleName -notin @('title', 'subtitle')) {
                continue
            }
            $shapeName = "ph--$($role.id)--$($placeholder.name)"
            $shape = $slide.Shapes.Item($shapeName)
            if (-not ([string]$shape.TextFrame.TextRange.Text).Contains([string][char]11)) {
                continue
            }
            $breakKey = "$( [string]$role.id ).$( [string]$placeholder.name )"
            if ($semanticBreaks -notcontains $breakKey) {
                $semanticBreaks += $breakKey
            }
        }
    }

    $presentation.SaveAs($outputPath, $ppSaveAsOpenXMLPresentation)

    if ($PreviewDir) {
        $previewPath = [System.IO.Path]::GetFullPath($PreviewDir)
        New-Item -ItemType Directory -Force -Path $previewPath | Out-Null
        $presentation.Export($previewPath, 'PNG', 1600, 900)
    }

    [pscustomobject]@{
        output = $outputPath
        layouts = $manifest.roles.Count
        slides = $presentation.Slides.Count
        slide_width = $slideWidth
        slide_height = $slideHeight
        semantic_breaks = $semanticBreaks
    } | ConvertTo-Json -Compress
}
finally {
    if ($presentation) {
        try { $presentation.Close() } catch {}
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)
    }
    if ($powerPoint) {
        try { $powerPoint.Quit() } catch {}
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
