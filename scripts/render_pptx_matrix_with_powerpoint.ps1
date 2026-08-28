param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][string]$ReportPath
)

$ErrorActionPreference = "Stop"
$inputFull = (Resolve-Path -LiteralPath $InputDir).Path
$outputFull = [IO.Path]::GetFullPath($OutputDir)
$reportFull = [IO.Path]::GetFullPath($ReportPath)
[IO.Directory]::CreateDirectory($outputFull) | Out-Null
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($reportFull)) | Out-Null

$files = Get-ChildItem -LiteralPath $inputFull -Filter '*.pptx' -File | Sort-Object Name
$rows = [Collections.Generic.List[object]]::new()
$app = New-Object -ComObject PowerPoint.Application
try {
    $app.DisplayAlerts = 1
    foreach ($file in $files) {
        $theme = $file.BaseName
        $themeOut = Join-Path $outputFull $theme
        [IO.Directory]::CreateDirectory($themeOut) | Out-Null
        $pres = $null
        try {
            $pres = $app.Presentations.Open($file.FullName, $true, $false, $false)
            $slideCount = $pres.Slides.Count
            $pres.Export($themeOut, 'PNG', 1280, 720)
            $rendered = @(Get-ChildItem -LiteralPath $themeOut -Filter '*.PNG' -File).Count
            $rows.Add([pscustomobject]@{
                theme = $theme
                status = $(if ($rendered -eq $slideCount) { 'pass' } else { 'fail' })
                slides = $slideCount
                rendered = $rendered
                output_dir = $themeOut
            })
        }
        catch {
            $rows.Add([pscustomobject]@{
                theme = $theme
                status = 'fail'
                slides = 0
                rendered = 0
                output_dir = $themeOut
                error = $_.Exception.Message
            })
        }
        finally {
            if ($pres) { $pres.Close() }
        }
        Write-Output ($rows[$rows.Count - 1] | ConvertTo-Json -Compress)
    }
}
finally {
    $app.Quit()
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) | Out-Null
}

$report = [pscustomobject]@{
    files = $files.Count
    slides = ($rows | Measure-Object -Property slides -Sum).Sum
    rendered = ($rows | Measure-Object -Property rendered -Sum).Sum
    failures = @($rows | Where-Object { $_.status -ne 'pass' }).Count
    results = $rows
}
[IO.File]::WriteAllText($reportFull, ($report | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
Write-Output ($report | Select-Object files, slides, rendered, failures | ConvertTo-Json -Compress)
