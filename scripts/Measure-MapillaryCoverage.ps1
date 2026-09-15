param(
    [switch]$SelfTest,
    [switch]$CheckConfig,
    [string]$CandidateConfig = 'config/pune-candidates.json'
)
$ErrorActionPreference = 'Stop'
$culture = [Globalization.CultureInfo]::InvariantCulture

function Get-DistanceMetres($a, $b) {
    $rad = [Math]::PI / 180
    $dlat = ($b[1] - $a[1]) * $rad
    $dlon = ($b[0] - $a[0]) * $rad
    $h = [Math]::Pow([Math]::Sin($dlat / 2), 2) + [Math]::Cos($a[1] * $rad) * [Math]::Cos($b[1] * $rad) * [Math]::Pow([Math]::Sin($dlon / 2), 2)
    return 6371000 * 2 * [Math]::Asin([Math]::Sqrt([Math]::Min(1.0, $h)))
}
function Select-SpacedImages($images) {
    foreach ($group in ($images | Group-Object sequence)) {
        $last = $null
        foreach ($item in ($group.Group | Sort-Object captured_at, id)) {
            if ($null -eq $last -or (Get-DistanceMetres $last.geometry.coordinates $item.geometry.coordinates) -ge 5) {
                $item
                $last = $item
            }
        }
    }
}
# A sequence ID is not a place. Crowdsourced uploads routinely split one short ride into
# many single-frame sequences at the same corner, so a sequence count overstates how many
# independent sites a candidate really offers. Merge sequence centroids that sit within
# $MergeMetres of each other and report the surviving count.
function Measure-DistinctSites($images, $mergeMetres = 40) {
    $centroids = foreach ($group in ($images | Group-Object sequence)) {
        $lon = ($group.Group | ForEach-Object { [double]$_.geometry.coordinates[0] } | Measure-Object -Average).Average
        $lat = ($group.Group | ForEach-Object { [double]$_.geometry.coordinates[1] } | Measure-Object -Average).Average
        [pscustomobject]@{ sequence = $group.Name; count = $group.Count; point = @($lon, $lat) }
    }
    $sites = @()
    foreach ($centroid in (@($centroids) | Sort-Object count -Descending)) {
        $match = $null
        foreach ($site in $sites) {
            if ((Get-DistanceMetres $site.point $centroid.point) -lt $mergeMetres) { $match = $site; break }
        }
        if ($match) {
            $match.sequences += $centroid.sequence
            $match.frames += $centroid.count
        } else {
            $sites += [pscustomobject]@{ point = $centroid.point; sequences = @($centroid.sequence); frames = $centroid.count }
        }
    }
    return $sites
}
if ($SelfTest) {
    $testDistance = Get-DistanceMetres @(0,0) @(0,0.001)
    if ([Math]::Abs($testDistance - 111.195) -gt 0.1) { throw "Distance test failed: $testDistance" }
    $sample = @(
        [pscustomobject]@{id='1';sequence='a';captured_at=1;geometry=@{coordinates=@(0,0)}},
        [pscustomobject]@{id='2';sequence='a';captured_at=2;geometry=@{coordinates=@(0,0.00001)}},
        [pscustomobject]@{id='3';sequence='a';captured_at=3;geometry=@{coordinates=@(0,0.0001)}},
        [pscustomobject]@{id='4';sequence='b';captured_at=1;geometry=@{coordinates=@(0,0)}}
    )
    $selected = @(Select-SpacedImages $sample)
    if (($selected.id -join ',') -ne '1,3,4') { throw 'Spacing or sequence isolation test failed' }
    # Three sequence IDs, two places: 'a' and 'b' share a corner, 'far' is ~1.1 km away.
    $siteSample = @(
        [pscustomobject]@{id='1';sequence='a';geometry=@{coordinates=@(0,0)}},
        [pscustomobject]@{id='2';sequence='b';geometry=@{coordinates=@(0,0.0001)}},
        [pscustomobject]@{id='3';sequence='far';geometry=@{coordinates=@(0,0.01)}}
    )
    $sites = @(Measure-DistinctSites $siteSample 40)
    if ($sites.Count -ne 2) { throw "Distinct-site test failed: got $($sites.Count) sites, expected 2" }
    if (@($sites | Where-Object { $_.sequences.Count -eq 2 }).Count -ne 1) { throw 'Distinct-site test failed: co-located sequences were not merged' }
    Write-Output 'PASS: known distance, five-metre spacing, independent sequence handling, and distinct-site merging.'
    exit 0
}

$root = Split-Path $PSScriptRoot -Parent
$config = Get-Content -Raw -LiteralPath (Join-Path $root $CandidateConfig) | ConvertFrom-Json
$candidates = @($config.candidates)
if ($candidates.Count -lt 1) { throw 'Candidate configuration is empty.' }
$seenNames = @{}
foreach ($candidate in $candidates) {
    if ($candidate.name -notmatch '^[a-z0-9_]+$' -or $seenNames.ContainsKey($candidate.name)) { throw 'Candidate names must be unique simple identifiers.' }
    $seenNames[$candidate.name] = $true
    if ($candidate.bbox.Count -ne 4) { throw 'Each candidate needs four bounding-box coordinates.' }
    $b = $candidate.bbox
    if ($b[0] -lt -180 -or $b[2] -gt 180 -or $b[1] -lt -90 -or $b[3] -gt 90 -or $b[0] -ge $b[2] -or $b[1] -ge $b[3]) { throw 'Invalid bounding box.' }
    $nx = [int][Math]::Ceiling([Math]::Round(($b[2]-$b[0])/0.002,8))
    $ny = [int][Math]::Ceiling([Math]::Round(($b[3]-$b[1])/0.002,8))
    if ($nx*$ny -gt 100) { throw 'Screening is limited to 100 small cells per candidate.' }
    Write-Output "$($candidate.name): validated $nx x $ny cells."
}
if ($CheckConfig) { exit 0 }
$token = $null
foreach ($line in Get-Content -LiteralPath (Join-Path $root '.env')) {
    if ($line -match '^\s*MAPILLARY_TOKEN\s*=\s*(.*?)\s*$') { $token = $Matches[1].Trim().Trim('"').Trim("'"); break }
}
if ([string]::IsNullOrWhiteSpace($token) -or $token -notmatch '^MLY\|') { throw 'Configure the Client Token in .env first.' }
$headers = @{Authorization="OAuth $token"}
$fields = 'id,geometry,sequence,captured_at,compass_angle,camera_type,camera_parameters,width,height,computed_geometry,computed_compass_angle'

function Get-MapillaryPage([string]$uri) {
    $parsed = [Uri]$uri
    if ($parsed.Scheme -ne 'https' -or $parsed.Host -ne 'graph.mapillary.com') { throw 'Unexpected pagination host; request stopped.' }
    for ($attempt=0; $attempt -lt 3; $attempt++) {
        try { return Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 30 -ErrorAction Stop }
        catch {
            $code = 'unavailable'
            try { $code = [string](($_.ErrorDetails.Message | ConvertFrom-Json).error.code) } catch {}
            if ($code -eq '190') { throw 'Mapillary authentication failed (190).' }
            if ($attempt -eq 2) { throw "Mapillary request failed; API code $code. Sensitive details withheld." }
            Start-Sleep -Seconds ([Math]::Pow(2, $attempt + 1))
        }
    }
}

# Preliminary search rectangles come from the explicit study configuration.
$now = [DateTimeOffset]::UtcNow
$cutoff = $now.AddMonths(-24).ToUnixTimeMilliseconds()
$outputDir = Join-Path $root ('reports/coverage/' + $now.ToString('yyyyMMdd-HHmmss'))
[IO.Directory]::CreateDirectory($outputDir) | Out-Null
[IO.File]::WriteAllText((Join-Path $outputDir 'candidate-config.json'), ($config | ConvertTo-Json -Depth 12))
$summaries = @()
foreach ($candidate in $candidates) {
    $unique = @{}
    $failures = @()
    $requests = 0
    $nx = [int][Math]::Ceiling([Math]::Round(($candidate.bbox[2]-$candidate.bbox[0])/0.002,8))
    $ny = [int][Math]::Ceiling([Math]::Round(($candidate.bbox[3]-$candidate.bbox[1])/0.002,8))
    for ($ix=0; $ix -lt $nx; $ix++) {
        for ($iy=0; $iy -lt $ny; $iy++) {
            $west = $candidate.bbox[0] + $ix * 0.002
            $south = $candidate.bbox[1] + $iy * 0.002
            $cell = @($west,$south,([Math]::Min([double]$candidate.bbox[2],$west+0.002)),([Math]::Min([double]$candidate.bbox[3],$south+0.002)))
            $bboxString = ($cell | ForEach-Object { $_.ToString('F6',$culture) }) -join ','
            $uri = "https://graph.mapillary.com/images?bbox=$bboxString&limit=1000&fields=$fields"
            try {
                for ($page=0; $page -lt 10; $page++) {
                    $response = Get-MapillaryPage $uri
                    $requests++
                    foreach ($item in $response.data) {
                        if ($null -eq $item.id) { continue }
                        $c = $item.geometry.coordinates
                        if ($c.Count -ne 2) { continue }
                        if ($c[0] -lt $candidate.bbox[0] -or $c[0] -gt $candidate.bbox[2] -or $c[1] -lt $candidate.bbox[1] -or $c[1] -gt $candidate.bbox[3]) { continue }
                        $unique[[string]$item.id] = $item
                    }
                    $uri = $response.paging.next
                    if ([string]::IsNullOrWhiteSpace($uri)) { break }
                }
                if (-not [string]::IsNullOrWhiteSpace($uri)) { $failures += "Cell $ix,$iy reached the ten-page safety cap; counts are incomplete." }
            } catch {
                $failures += "Cell $ix,$iy could not be fully queried."
                Write-Output "$($candidate.name): cell $ix,$iy failed; recording incomplete coverage."
                if ($_.Exception.Message -like '*authentication*') { throw 'Authentication failed; stopped.' }
            }
            Write-Output "$($candidate.name): cell $ix,$iy done; $($unique.Count) unique images so far."
        }
    }
    $all = @($unique.Values | Sort-Object captured_at, id)
    $recent = @($all | Where-Object { $null -ne $_.captured_at -and $_.captured_at -ge $cutoff -and $_.captured_at -le $now.ToUnixTimeMilliseconds() })
    $eligible = @($recent | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_.sequence) -and $null -ne $_.compass_angle -and $_.compass_angle -ge 0 -and $_.compass_angle -lt 360 -and $_.width -gt 0 -and $_.height -gt 0
    })
    $spaced = @(Select-SpacedImages $eligible)
    $dated = @($all | Where-Object { $null -ne $_.captured_at -and $_.captured_at -gt 0 })
    $sequenceCount = @($spaced | Select-Object -ExpandProperty sequence -Unique).Count
    $sites = @(Measure-DistinctSites $spaced 40)
    $summary = [ordered]@{
        name=$candidate.name; label=$candidate.label; bbox=$candidate.bbox; unique_images=$all.Count; recent_images=$recent.Count
        metadata_eligible_recent=$eligible.Count; spaced_recent_images=$spaced.Count; spaced_recent_sequences=$sequenceCount
        distinct_sites=$sites.Count
        site_breakdown=@($sites | Sort-Object frames -Descending | ForEach-Object {
            @{ longitude=[Math]::Round($_.point[0],5); latitude=[Math]::Round($_.point[1],5); frames=$_.frames; sequence_ids=$_.sequences.Count }
        })
        all_sequences=@($all | Where-Object { $_.sequence } | Select-Object -ExpandProperty sequence -Unique).Count
        oldest_capture=$null; newest_capture=$null
        camera_types=@($all | Group-Object camera_type | ForEach-Object { @{type=$_.Name;count=$_.Count} })
        images_with_camera_parameters=@($all | Where-Object { $_.camera_parameters.Count -gt 0 }).Count
        images_with_compass=@($all | Where-Object { $null -ne $_.compass_angle }).Count
        images_with_corrected_position=@($all | Where-Object { $null -ne $_.computed_geometry }).Count
        successful_pages=$requests; complete=($failures.Count -eq 0); problems=$failures
        # Gate on distinct places, not sequence IDs: co-located sequences cannot give a
        # leakage-free split. Round 1 in Pune returned 23 sequence IDs across 13 sites.
        metadata_gate=($failures.Count -eq 0 -and $spaced.Count -ge 300 -and $sites.Count -ge 3)
        metadata_gate_note='Sequence-ID count is reported for reference only; the gate uses distinct_sites.'
        visual_quality_and_waste_presence='Not inspected; metadata alone cannot establish usable training data.'
        capture_years=@($dated | Group-Object { [DateTimeOffset]::FromUnixTimeMilliseconds([long]$_.captured_at).Year } | ForEach-Object { @{year=$_.Name;count=$_.Count} })
        sample_image_links=@($all | Select-Object -Last 5 | ForEach-Object { "https://www.mapillary.com/app/?pKey=$($_.id)" })
    }
    if ($dated.Count -gt 0) {
        $summary.oldest_capture = [DateTimeOffset]::FromUnixTimeMilliseconds([long]$dated[0].captured_at).ToString('yyyy-MM-dd')
        $summary.newest_capture = [DateTimeOffset]::FromUnixTimeMilliseconds([long]$dated[-1].captured_at).ToString('yyyy-MM-dd')
    }
    # Persist image metadata only: never pagination URLs, headers or access tokens.
    $json = ConvertTo-Json -InputObject $all -Depth 12
    [IO.File]::WriteAllText((Join-Path $outputDir ($candidate.name + '-images.json')), $json)
    $summaries += [pscustomobject]$summary
    Write-Output "$($candidate.name): recent=$($recent.Count), after spacing=$($spaced.Count), sequence ids=$sequenceCount, distinct sites=$($sites.Count), complete=$($summary.complete)"
}
$report = @{study=$config.study;checked_at=$now.ToString('o');recent_cutoff=[DateTimeOffset]::FromUnixTimeMilliseconds($cutoff).ToString('yyyy-MM-dd');candidates=$summaries}
[IO.File]::WriteAllText((Join-Path $outputDir 'summary.json'), ($report | ConvertTo-Json -Depth 12))
Write-Output "Saved coverage results to $outputDir"
$summaries | Select-Object name,unique_images,recent_images,spaced_recent_images,spaced_recent_sequences,distinct_sites,oldest_capture,newest_capture,complete,metadata_gate | Format-Table -AutoSize
