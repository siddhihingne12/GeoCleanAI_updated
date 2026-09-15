param(
    # Extracted YOLO export folder containing data.yaml and split/images + split/labels.
    [Parameter(Mandatory = $true)]
    [string]$Folder,
    # Short identifier used for report and sheet names, e.g. garbage_can_overflow.
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [int]$PerClass = 8
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-z0-9_]+$') { throw 'Name must be a simple lowercase identifier.' }
if ($PerClass -lt 1 -or $PerClass -gt 24) { throw 'Choose between 1 and 24 samples per class.' }
$root = Split-Path $PSScriptRoot -Parent
$source = $Folder
if (-not [IO.Path]::IsPathRooted($source)) { $source = Join-Path $root $Folder }
$yaml = Join-Path $source 'data.yaml'
if (-not (Test-Path -LiteralPath $yaml)) { throw 'data.yaml not found; expected an extracted YOLO export folder.' }
Add-Type -AssemblyName System.Drawing
$culture = [Globalization.CultureInfo]::InvariantCulture

# Class names: Roboflow writes either an inline list or a block list under names:.
$yamlText = Get-Content -Raw -LiteralPath $yaml
$names = @()
if ($yamlText -match 'names:\s*\[(.*?)\]') {
    $names = @($Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim("'").Trim('"') })
} else {
    $inNames = $false
    foreach ($line in ($yamlText -split "`r?`n")) {
        if ($line -match '^names:\s*$') { $inNames = $true; continue }
        if (-not $inNames) { continue }
        if ($line -match '^\s+-\s*(.+)$') { $names += $Matches[1].Trim().Trim("'").Trim('"') }
        elseif ($line -match '^\s+\d+\s*:\s*(.+)$') { $names += $Matches[1].Trim().Trim("'").Trim('"') }
        elseif ($line -match '^\S') { break }
    }
}
if ($names.Count -lt 1) { throw 'No class names could be read from data.yaml.' }

$imageIndex = @{}
foreach ($im in (Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object { $_.Directory.Name -eq 'images' })) {
    $imageIndex["$($im.Directory.Parent.FullName)|$([IO.Path]::GetFileNameWithoutExtension($im.Name))"] = $im.FullName
}

$records = foreach ($label in (Get-ChildItem -LiteralPath $source -Recurse -File -Filter *.txt | Where-Object { $_.Directory.Name -eq 'labels' })) {
    $key = "$($label.Directory.Parent.FullName)|$([IO.Path]::GetFileNameWithoutExtension($label.Name))"
    if (-not $imageIndex.ContainsKey($key)) { continue }
    $boxes = @(foreach ($line in [IO.File]::ReadAllLines($label.FullName)) {
        $parts = @($line.Trim() -split '\s+' | Where-Object { $_ -ne '' })
        if ($parts.Count -lt 5) { continue }
        $values = @($parts[1..($parts.Count - 1)] | ForEach-Object { [double]::Parse($_, $culture) })
        if ($values.Count -eq 4) {
            $x1 = $values[0] - $values[2] / 2; $y1 = $values[1] - $values[3] / 2
            $x2 = $values[0] + $values[2] / 2; $y2 = $values[1] + $values[3] / 2
        } else {
            # Polygon labels: use the bounding extent of the points.
            $xs = @(for ($i = 0; $i -lt $values.Count - 1; $i += 2) { $values[$i] })
            $ys = @(for ($i = 1; $i -lt $values.Count; $i += 2) { $values[$i] })
            $x1 = ($xs | Measure-Object -Minimum).Minimum; $x2 = ($xs | Measure-Object -Maximum).Maximum
            $y1 = ($ys | Measure-Object -Minimum).Minimum; $y2 = ($ys | Measure-Object -Maximum).Maximum
        }
        [pscustomobject]@{ cls = [int]$parts[0]; x1 = $x1; y1 = $y1; x2 = $x2; y2 = $y2; area = [Math]::Max(0.0, ($x2 - $x1) * ($y2 - $y1)) }
    })
    [pscustomobject]@{ split = $label.Directory.Parent.Name; image = $imageIndex[$key]; file = [IO.Path]::GetFileName($imageIndex[$key]); boxes = $boxes }
}
$records = @($records)
if ($records.Count -lt 1) { throw 'No labelled images were found.' }

function Get-Median($values) {
    $sorted = @($values | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    return $sorted[[int][Math]::Floor(($sorted.Count - 1) / 2)]
}

$sheetDir = Join-Path $root "data/public/_inventory/$Name"
[IO.Directory]::CreateDirectory($sheetDir) | Out-Null
$font = New-Object Drawing.Font('Arial', 10, [Drawing.FontStyle]::Bold)
$targetPen = New-Object Drawing.Pen([Drawing.Color]::Red, 3)
$otherPen = New-Object Drawing.Pen([Drawing.Color]::Yellow, 1)
$tileW = 480; $tileH = 380; $columns = 4

$classStats = for ($c = 0; $c -lt $names.Count; $c++) {
    $withClass = @($records | Where-Object { @($_.boxes | Where-Object { $_.cls -eq $c }).Count -gt 0 } | Sort-Object split, file)
    $classBoxes = @($records | ForEach-Object { $_.boxes } | Where-Object { $_.cls -eq $c })
    if ($withClass.Count -gt 0) {
        $take = [Math]::Min($PerClass, $withClass.Count)
        $picks = for ($i = 0; $i -lt $take; $i++) { $withClass[[int][Math]::Floor(($i + 0.5) * $withClass.Count / $take)] }
        $rowsNeeded = [int][Math]::Ceiling($take / $columns)
        $sheet = New-Object Drawing.Bitmap(($tileW * $columns), ($tileH * $rowsNeeded))
        $g = [Drawing.Graphics]::FromImage($sheet)
        $g.Clear([Drawing.Color]::White)
        $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        for ($i = 0; $i -lt $take; $i++) {
            $x0 = ($i % $columns) * $tileW; $y0 = [Math]::Floor($i / $columns) * $tileH + 18
            $img = [Drawing.Image]::FromFile($picks[$i].image)
            try {
                $scale = [Math]::Min($tileW / $img.Width, ($tileH - 18) / $img.Height)
                $w = $img.Width * $scale; $h = $img.Height * $scale
                $g.DrawImage($img, [single]$x0, [single]$y0, [single]$w, [single]$h)
                foreach ($b in $picks[$i].boxes) {
                    $pen = $otherPen
                    if ($b.cls -eq $c) { $pen = $targetPen }
                    $g.DrawRectangle($pen, [single]($x0 + $b.x1 * $w), [single]($y0 + $b.y1 * $h), [single](($b.x2 - $b.x1) * $w), [single](($b.y2 - $b.y1) * $h))
                }
            } finally { $img.Dispose() }
            $caption = "$($picks[$i].split)/$($picks[$i].file)"
            if ($caption.Length -gt 60) { $caption = $caption.Substring(0, 60) }
            $g.DrawString($caption, $font, [Drawing.Brushes]::Black, [single]($x0 + 3), [single]($y0 - 17))
        }
        $safe = ($names[$c] -replace '[^A-Za-z0-9_-]+', '_').Trim('_')
        if ([string]::IsNullOrEmpty($safe)) { $safe = 'unnamed' }
        $sheet.Save((Join-Path $sheetDir "class-$c-$safe.jpg"), [Drawing.Imaging.ImageFormat]::Jpeg)
        $g.Dispose(); $sheet.Dispose()
    }
    [ordered]@{
        id = $c; name = $names[$c]; images = $withClass.Count; boxes = $classBoxes.Count
        median_box_area_fraction = (Get-Median ($classBoxes | ForEach-Object area))
        images_by_split = @($withClass | Group-Object split | ForEach-Object { "$($_.Name):$($_.Count)" })
    }
}
$font.Dispose(); $targetPen.Dispose(); $otherPen.Dispose()

$report = [ordered]@{
    name = $Name; source_folder = $source; checked_at = [DateTimeOffset]::UtcNow.ToString('o')
    labelled_images = $records.Count; background_images = @($records | Where-Object { $_.boxes.Count -eq 0 }).Count
    images_by_split = @($records | Group-Object split | ForEach-Object { "$($_.Name):$($_.Count)" })
    classes = @($classStats)
}
$reportDir = Join-Path $root 'reports/public-datasets'
[IO.Directory]::CreateDirectory($reportDir) | Out-Null
$reportPath = Join-Path $reportDir "$Name-labels.json"
[IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 6))
$classStats | ForEach-Object { [pscustomobject]$_ } | Select-Object id, name, images, boxes, median_box_area_fraction | Format-Table -AutoSize
Write-Output "Labelled images: $($records.Count); background (no boxes): $($report.background_images)"
Write-Output "Class sheets saved to $sheetDir"
Write-Output "Saved label summary to $reportPath"
