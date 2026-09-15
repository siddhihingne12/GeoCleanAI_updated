param(
    [Parameter(Mandatory = $true)]
    [string]$Folder,
    # Short identifier used for report and contact-sheet names, e.g. qr4change.
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [int]$SamplesPerFolder = 12,
    [switch]$SkipSheets
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-z0-9_]+$') { throw 'Name must be a simple lowercase identifier.' }
if ($SamplesPerFolder -lt 1 -or $SamplesPerFolder -gt 48) { throw 'Choose between 1 and 48 samples per folder.' }
$root = Split-Path $PSScriptRoot -Parent
$source = $Folder
if (-not [IO.Path]::IsPathRooted($source)) { $source = Join-Path $root $Folder }
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "Folder not found: $Folder" }
$source = (Resolve-Path -LiteralPath $source).Path.TrimEnd('\')
Add-Type -AssemblyName System.Drawing

$extensions = @('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff')
$files = @(Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() })
if ($files.Count -lt 1) { throw 'No image files found.' }
Write-Output "Found $($files.Count) image files under $source."

function Get-Median($values) {
    $sorted = @($values | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    return $sorted[[int][Math]::Floor(($sorted.Count - 1) / 2)]
}

$rows = foreach ($f in $files) {
    $relativeDir = $f.DirectoryName.Substring($source.Length).TrimStart('\')
    if ([string]::IsNullOrEmpty($relativeDir)) { $relativeDir = '.' }
    $width = $null; $height = $null; $readable = $true
    try {
        # Read the header only; full decoding of thousands of photos is unnecessary here.
        $stream = [IO.File]::OpenRead($f.FullName)
        try {
            $img = [Drawing.Image]::FromStream($stream, $false, $false)
            try { $width = $img.Width; $height = $img.Height } finally { $img.Dispose() }
        } finally { $stream.Dispose() }
    } catch { $readable = $false }
    [pscustomobject]@{
        folder = $relativeDir; file = $f.Name; path = $f.FullName; ext = $f.Extension.ToLowerInvariant()
        bytes = $f.Length; width = $width; height = $height; readable = $readable
        sha256 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    }
}

$folders = @($rows | Group-Object folder | Sort-Object Name | ForEach-Object {
    $ok = @($_.Group | Where-Object readable)
    [ordered]@{
        folder = $_.Name; images = $_.Count; unreadable = $_.Count - $ok.Count
        extensions = @($_.Group | Group-Object ext | ForEach-Object { "$($_.Name):$($_.Count)" })
        width_min = ($ok | Measure-Object width -Minimum).Minimum; width_median = (Get-Median ($ok | ForEach-Object width)); width_max = ($ok | Measure-Object width -Maximum).Maximum
        height_min = ($ok | Measure-Object height -Minimum).Minimum; height_median = (Get-Median ($ok | ForEach-Object height)); height_max = ($ok | Measure-Object height -Maximum).Maximum
        under_640px_short_side = @($ok | Where-Object { [Math]::Min($_.width, $_.height) -lt 640 }).Count
        portrait = @($ok | Where-Object { $_.height -gt $_.width }).Count
    }
})

# Exact duplicates inflate counts and leak across splits. A duplicate that sits in two
# different class folders is also a label conflict, so report those separately.
$dupeGroups = @($rows | Group-Object sha256 | Where-Object Count -gt 1)
$crossFolder = @($dupeGroups | Where-Object { @($_.Group | Select-Object -ExpandProperty folder -Unique).Count -gt 1 } | ForEach-Object {
    [ordered]@{ sha256 = $_.Name; copies = @($_.Group | ForEach-Object { "$($_.folder)\$($_.file)" }) }
})

$reportDir = Join-Path $root 'reports/public-datasets'
[IO.Directory]::CreateDirectory($reportDir) | Out-Null
$sheetDir = Join-Path $root "data/public/_inventory/$Name"

if (-not $SkipSheets) {
    [IO.Directory]::CreateDirectory($sheetDir) | Out-Null
    $font = New-Object Drawing.Font('Arial', 11, [Drawing.FontStyle]::Bold)
    $tile = 400; $columns = 4
    foreach ($group in ($rows | Where-Object readable | Group-Object folder)) {
        $ordered = @($group.Group | Sort-Object file)
        $take = [Math]::Min($SamplesPerFolder, $ordered.Count)
        $picks = for ($i = 0; $i -lt $take; $i++) { $ordered[[int][Math]::Floor(($i + 0.5) * $ordered.Count / $take)] }
        $rowsNeeded = [int][Math]::Ceiling($take / $columns)
        $sheet = New-Object Drawing.Bitmap(($tile * $columns), ($tile * $rowsNeeded))
        $g = [Drawing.Graphics]::FromImage($sheet)
        $g.Clear([Drawing.Color]::White)
        $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        for ($i = 0; $i -lt $take; $i++) {
            $x = ($i % $columns) * $tile; $y = [Math]::Floor($i / $columns) * $tile
            $img = [Drawing.Image]::FromFile($picks[$i].path)
            try {
                $scale = [Math]::Min($tile / $img.Width, ($tile - 22) / $img.Height)
                $g.DrawImage($img, $x, ($y + 22), [int]($img.Width * $scale), [int]($img.Height * $scale))
            } finally { $img.Dispose() }
            $g.DrawString($picks[$i].file, $font, [Drawing.Brushes]::Black, ($x + 4), ($y + 3))
        }
        $safe = ($group.Name -replace '[^A-Za-z0-9_-]+', '_').Trim('_')
        if ([string]::IsNullOrEmpty($safe)) { $safe = 'root' }
        $sheet.Save((Join-Path $sheetDir "sheet-$safe.jpg"), [Drawing.Imaging.ImageFormat]::Jpeg)
        $g.Dispose(); $sheet.Dispose()
    }
    $font.Dispose()
    Write-Output "Contact sheets saved to $sheetDir"
}

$report = [ordered]@{
    name = $Name; source_folder = $source; checked_at = [DateTimeOffset]::UtcNow.ToString('o')
    image_files = $rows.Count; unreadable = @($rows | Where-Object { -not $_.readable }).Count
    duplicate_groups = $dupeGroups.Count; duplicate_extra_copies = (($dupeGroups | Measure-Object Count -Sum).Sum - $dupeGroups.Count)
    cross_folder_duplicates = $crossFolder; folders = $folders
}
$reportPath = Join-Path $reportDir "$Name-inventory.json"
[IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 8))
$folders | ForEach-Object { [pscustomobject]$_ } | Select-Object folder, images, unreadable, width_median, height_median, under_640px_short_side | Format-Table -AutoSize
Write-Output "Exact duplicate groups: $($dupeGroups.Count); cross-folder duplicates: $($crossFolder.Count)"
Write-Output "Saved inventory to $reportPath"
