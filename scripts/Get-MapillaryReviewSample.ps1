param(
    [string]$MetadataFile = 'reports/coverage/20260912-142113/candidate_b-images.json',
    [string]$OutputFolder = 'reports/visual-review/candidate-b',
    [int]$PerSequence = 3,
    # Review only frames that passed the freshness gate. Zero inspects every capture date.
    [int]$SinceMonths = 24,
    # Optional exact sequence filter for a focused follow-up around an ambiguous frame.
    [string]$SequenceId = '',
    # Optional focus frame; when set, keep a compact temporal window around it.
    [string]$FocusImageId = ''
)
$ErrorActionPreference = 'Stop'
if ($PerSequence -lt 1 -or $PerSequence -gt 9) { throw 'Choose between one and nine samples per sequence.' }
$root = Split-Path $PSScriptRoot -Parent
$images = Get-Content -Raw -LiteralPath (Join-Path $root $MetadataFile) | ConvertFrom-Json
if ($SinceMonths -gt 0) {
    $cutoff = [DateTimeOffset]::UtcNow.AddMonths(-$SinceMonths).ToUnixTimeMilliseconds()
    $before = @($images).Count
    $images = @($images | Where-Object { $null -ne $_.captured_at -and $_.captured_at -ge $cutoff })
    Write-Output "Freshness filter kept $($images.Count) of $before frames from the last $SinceMonths months."
    if ($images.Count -lt 1) { throw 'No frames remain after the freshness filter; this candidate failed the coverage gate.' }
}
if (-not [string]::IsNullOrWhiteSpace($SequenceId)) {
    $images = @($images | Where-Object { $_.sequence -eq $SequenceId })
    Write-Output "Sequence filter kept $($images.Count) frames from $SequenceId."
    if ($images.Count -lt 1) { throw "No frames matched sequence $SequenceId." }
}
if (-not [string]::IsNullOrWhiteSpace($FocusImageId)) {
    $orderedFocus = @($images | Sort-Object captured_at,id)
    $focusIndex = -1
    for ($i = 0; $i -lt $orderedFocus.Count; $i++) {
        if ([string]$orderedFocus[$i].id -eq $FocusImageId) { $focusIndex = $i; break }
    }
    if ($focusIndex -lt 0) { throw "Focus image $FocusImageId was not found after filtering." }
    $windowSize = [Math]::Min($PerSequence, $orderedFocus.Count)
    $start = [Math]::Max(0, $focusIndex - [Math]::Floor($windowSize / 2))
    $start = [Math]::Min($start, $orderedFocus.Count - $windowSize)
    $images = @($orderedFocus[$start..($start + $windowSize - 1)])
    Write-Output "Focus window kept $($images.Count) adjacent frames around $FocusImageId."
}
$outputDir = Join-Path $root $OutputFolder
[IO.Directory]::CreateDirectory($outputDir) | Out-Null
$token = $null
foreach ($line in Get-Content -LiteralPath (Join-Path $root '.env')) {
    if ($line -match '^\s*MAPILLARY_TOKEN\s*=\s*(.*?)\s*$') { $token = $Matches[1].Trim().Trim('"').Trim("'"); break }
}
if ([string]::IsNullOrWhiteSpace($token) -or $token -notmatch '^MLY\|') { throw 'Configure the Client Token in .env first.' }
$manifest = @()
foreach ($group in ($images | Group-Object sequence | Sort-Object Name)) {
    $ordered = @($group.Group | Sort-Object captured_at,id)
    # A short sequence cannot yield distinct samples; never review the same frame twice.
    $take = [Math]::Min($PerSequence, $ordered.Count)
    for ($i=0; $i -lt $take; $i++) {
        $index = [int][Math]::Floor(($i + 0.5) * $ordered.Count / $take)
        if ($index -ge $ordered.Count) { $index = $ordered.Count - 1 }
        $item = $ordered[$index]
        $filename = "$($item.id).jpg"
        $path = Join-Path $outputDir $filename
        $status = 'downloaded'
        $creator = $null
        try {
            $uri = "https://graph.mapillary.com/$($item.id)?fields=id,thumb_2048_url,creator"
            $meta = Invoke-RestMethod -Uri $uri -Headers @{Authorization="OAuth $token"} -TimeoutSec 30
            $creator = $meta.creator
            if (-not (Test-Path -LiteralPath $path)) {
                $thumbUri = [Uri]$meta.thumb_2048_url
                if ($thumbUri.Scheme -ne 'https') { throw 'Unexpected image URL scheme.' }
                # Download the API-provided image without forwarding the API token.
                Invoke-WebRequest -UseBasicParsing -Uri $thumbUri.AbsoluteUri -OutFile $path -TimeoutSec 60 | Out-Null
            }
            Write-Output "Downloaded sample $($item.id) from sequence $($group.Name)."
        } catch {
            $status = 'failed'
            Write-Output "Sample $($item.id) failed; sensitive request details withheld."
        }
        $manifest += [pscustomobject]@{
            image_id=$item.id;sequence_id=$group.Name;camera_type=$item.camera_type
            captured_at=[DateTimeOffset]::FromUnixTimeMilliseconds([long]$item.captured_at).ToString('o')
            coordinates=$item.geometry.coordinates;file=$filename;status=$status;creator=$creator
            mapillary_url="https://www.mapillary.com/app/?pKey=$($item.id)"
            original_width=$item.width;original_height=$item.height
        }
    }
}
[IO.File]::WriteAllText((Join-Path $outputDir 'manifest.json'), (ConvertTo-Json -InputObject $manifest -Depth 8))

# Mechanical contact sheets for inspection only. Downloaded source JPEGs are preserved.
Add-Type -AssemblyName System.Drawing
$font = New-Object Drawing.Font('Arial',16)
foreach ($group in ($manifest | Where-Object { $_.status -eq 'downloaded' } | Group-Object sequence_id)) {
    $rows = @($group.Group)
    $sheet = New-Object Drawing.Bitmap(2048, (1060 * $rows.Count))
    $graphics = [Drawing.Graphics]::FromImage($sheet)
    $graphics.Clear([Drawing.Color]::White)
    for ($j=0; $j -lt $rows.Count; $j++) {
        $row = $rows[$j]
        $source = [Drawing.Image]::FromFile((Join-Path $outputDir $row.file))
        try {
            $scale = [Math]::Min(2048.0/$source.Width, 1024.0/$source.Height)
            $width = [int]($source.Width*$scale)
            $height = [int]($source.Height*$scale)
            $graphics.DrawString("$($row.image_id) | $($row.captured_at.Substring(0,10)) | $($row.camera_type)",$font,[Drawing.Brushes]::Black,8,($j*1060+4))
            $graphics.DrawImage($source,0,($j*1060+36),$width,$height)
        } finally { $source.Dispose() }
    }
    $sheet.Save((Join-Path $outputDir ("sheet-$($group.Name).jpg")),[Drawing.Imaging.ImageFormat]::Jpeg)
    $graphics.Dispose()
    $sheet.Dispose()
}
$font.Dispose()
Write-Output "Review samples and contact sheets saved to $outputDir"
