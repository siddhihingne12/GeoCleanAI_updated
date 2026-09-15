param(
    [string]$Config = 'config/public-datasets.json',
    [string]$OutputRoot = 'data/public/roboflow',
    # Optional exact entry name from the config, e.g. garbage_can_overflow.
    [string]$Name = '',
    [string]$Format = 'yolov8',
    # Zero exports the newest version.
    [int]$Version = 0,
    # Read classes, counts, versions and licence fields without downloading images.
    [switch]$MetadataOnly,
    [switch]$CheckConfig
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$root = Split-Path $PSScriptRoot -Parent
$cfg = Get-Content -Raw -LiteralPath (Join-Path $root $Config) | ConvertFrom-Json
$entries = @($cfg.roboflow)
if (-not [string]::IsNullOrWhiteSpace($Name)) { $entries = @($entries | Where-Object { $_.name -eq $Name }) }
if ($entries.Count -lt 1) { throw 'No Roboflow entries matched the configuration.' }
if ($Format -notmatch '^[a-z0-9-]+$') { throw 'Invalid export format slug.' }
$seen = @{}
foreach ($e in $entries) {
    foreach ($field in 'name', 'workspace', 'project') {
        if ([string]::IsNullOrWhiteSpace($e.$field)) { throw "A Roboflow entry is missing '$field'." }
    }
    if ($e.name -notmatch '^[a-z0-9_]+$' -or $seen.ContainsKey($e.name)) { throw 'Entry names must be unique simple identifiers.' }
    if ($e.workspace -notmatch '^[A-Za-z0-9_-]+$' -or $e.project -notmatch '^[A-Za-z0-9_-]+$') { throw "Invalid workspace or project slug for $($e.name)." }
    $seen[$e.name] = $true
    Write-Output "$($e.name): $($e.workspace)/$($e.project) validated."
}
if ($CheckConfig) { exit 0 }

$apiKey = $null
foreach ($line in Get-Content -LiteralPath (Join-Path $root '.env')) {
    if ($line -match '^\s*ROBOFLOW_API_KEY\s*=\s*(.*?)\s*$') { $apiKey = $Matches[1].Trim().Trim('"').Trim("'"); break }
}
if ([string]::IsNullOrWhiteSpace($apiKey)) { throw 'Add ROBOFLOW_API_KEY=<your private API key> to .env first.' }

# The key travels only in the query string of api.roboflow.com requests. Error text,
# logs and saved files never include request URLs, and the signed export link is not saved.
function Invoke-Roboflow([string]$path) {
    $separator = '?'
    if ($path.Contains('?')) { $separator = '&' }
    $uri = "https://api.roboflow.com/$path$separator" + 'api_key=' + [Uri]::EscapeDataString($apiKey)
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        try { return Invoke-RestMethod -Uri $uri -TimeoutSec 60 -ErrorAction Stop }
        catch {
            $status = $null
            try { $status = [int]$_.Exception.Response.StatusCode } catch {}
            $shown = $path.Split('?')[0]
            if ($status -eq 401 -or $status -eq 403) { throw "Roboflow refused $shown (HTTP $status). Check ROBOFLOW_API_KEY; details withheld." }
            if ($status -eq 404) { throw "Roboflow returned 404 for $shown." }
            if ($attempt -eq 2) { throw "Roboflow request failed for $shown (HTTP $status); details withheld." }
            Start-Sleep -Seconds ([Math]::Pow(2, $attempt + 1))
        }
    }
}

# Windows PowerShell 5.1 cannot write paths over 260 characters, and Roboflow keeps the
# original filename plus a 32-character hash; Expand-Archive failed on the overflow set
# for that reason. Extract entry by entry instead, shortening long stems identically for
# an image and its label so every pair stays matched.
function Expand-RoboflowZip([string]$zipPath, [string]$destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $sha = [Security.Cryptography.SHA1]::Create()
    $renamed = 0
    $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        foreach ($entry in $archive.Entries) {
            if ([string]::IsNullOrEmpty($entry.Name)) { continue }
            $parts = @($entry.FullName -split '/' | Where-Object { $_ -ne '' })
            if ($parts -contains '..') { throw 'Archive entry escapes the destination; extraction stopped.' }
            $name = $parts[-1]
            $stem = [IO.Path]::GetFileNameWithoutExtension($name)
            if ($stem.Length -gt 80) {
                $digest = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($stem))[0..3] | ForEach-Object { $_.ToString('x2') })
                $name = $stem.Substring(0, 60) + '_' + $digest + [IO.Path]::GetExtension($name)
                $renamed++
            }
            $dir = $destination
            if ($parts.Count -gt 1) { $dir = Join-Path $destination (($parts[0..($parts.Count - 2)]) -join '\') }
            [IO.Directory]::CreateDirectory($dir) | Out-Null
            $target = Join-Path $dir $name
            if ($target.Length -gt 259) { throw "Path is still $($target.Length) characters after shortening; move the output folder closer to the drive root." }
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
        }
    } finally { $archive.Dispose(); $sha.Dispose() }
    return $renamed
}

$runStamp = [DateTimeOffset]::UtcNow
$summaries = @()
foreach ($e in $entries) {
    $info = Invoke-Roboflow "$($e.workspace)/$($e.project)"
    $p = $info.project
    if ($null -eq $p) { throw "Unexpected project response for $($e.name); top-level keys: $(($info.PSObject.Properties.Name) -join ', ')" }

    $classes = @()
    if ($null -ne $p.classes) {
        $classes = @($p.classes.PSObject.Properties | Sort-Object { [int]$_.Value } -Descending | ForEach-Object {
            [pscustomobject]@{ name = $_.Name; count = [int]$_.Value }
        })
    }
    $versions = @($info.versions | ForEach-Object {
        [pscustomobject]@{
            version = [int](([string]$_.id).Split('/')[-1]); images = $_.images; splits = $_.splits
            created = $_.created; exports = $_.exports
        }
    } | Sort-Object version)
    # Roboflow has used more than one field name for licences; keep every licence-like field verbatim.
    $licenceFields = @($p.PSObject.Properties | Where-Object { $_.Name -match 'licen' } | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join '; '

    $record = [ordered]@{
        name = $e.name; workspace = $e.workspace; project = $e.project; url = $e.url
        candidate_class = $e.candidate_class; listed_licence = $e.listed_licence
        api_licence_fields = $licenceFields; type = $p.type; annotation = $p.annotation
        images = $p.images; unannotated = $p.unannotated; classes = $classes; versions = $versions
        checked_at = $runStamp.ToString('o'); download = $null
    }
    $entryDir = Join-Path $root (Join-Path $OutputRoot $e.name)
    [IO.Directory]::CreateDirectory($entryDir) | Out-Null

    if (-not $MetadataOnly) {
        if ($versions.Count -lt 1) {
            Write-Output "$($e.name): no dataset versions are published; download skipped."
        } else {
            $v = $versions[-1].version
            if ($Version -gt 0) { $v = $Version }
            $deadline = [DateTime]::UtcNow.AddMinutes(10)
            do {
                $export = Invoke-Roboflow "$($e.workspace)/$($e.project)/$v/$Format`?nocache=true"
                $notReady = ($null -ne $export.PSObject.Properties['ready'] -and $export.ready -eq $false)
                if ($notReady) {
                    Write-Output ("$($e.name): export generating, progress {0:P0}" -f [double]$export.progress)
                    Start-Sleep -Seconds 3
                }
            } while ($notReady -and [DateTime]::UtcNow -lt $deadline)
            if ($notReady) { throw "$($e.name): export did not finish within 10 minutes." }
            $link = [string]$export.export.link
            if ([string]::IsNullOrWhiteSpace($link)) { throw "$($e.name): export response had no download link; keys: $(($export.PSObject.Properties.Name) -join ', ')" }
            $linkUri = [Uri]$link
            if ($linkUri.Scheme -ne 'https') { throw 'Unexpected export link scheme; download stopped.' }

            $zipName = "v$v-$Format.zip"
            $zip = Join-Path $entryDir $zipName
            $extract = Join-Path $entryDir "v$v-$Format"
            if (-not (Test-Path -LiteralPath $zip)) {
                Write-Output "$($e.name): downloading version $v ($Format)."
                Invoke-WebRequest -UseBasicParsing -Uri $linkUri.AbsoluteUri -OutFile $zip -TimeoutSec 1800 | Out-Null
            }
            $renamedNames = $null
            if (-not (Test-Path -LiteralPath $extract)) {
                $renamedNames = Expand-RoboflowZip $zip $extract
                Write-Output "$($e.name): extracted; $renamedNames long filenames shortened."
            }

            $splits = @(Get-ChildItem -LiteralPath $extract -Directory | ForEach-Object {
                $imageDir = Join-Path $_.FullName 'images'
                $labelDir = Join-Path $_.FullName 'labels'
                [pscustomobject]@{
                    split = $_.Name
                    images = @(if (Test-Path -LiteralPath $imageDir) { Get-ChildItem -LiteralPath $imageDir -File }).Count
                    labels = @(if (Test-Path -LiteralPath $labelDir) { Get-ChildItem -LiteralPath $labelDir -File -Filter *.txt }).Count
                }
            })
            # Roboflow exports ship a README with the dataset's own licence statement; keep those lines as evidence.
            $readmeLicence = @(Get-ChildItem -LiteralPath $extract -File -Filter 'README*' | ForEach-Object {
                Select-String -LiteralPath $_.FullName -Pattern 'licen' | ForEach-Object { $_.Line.Trim() }
            })
            $record.download = [ordered]@{
                version = $v; format = $Format; zip = "$OutputRoot/$($e.name)/$zipName"
                zip_bytes = (Get-Item -LiteralPath $zip).Length; folder = "$OutputRoot/$($e.name)/v$v-$Format"
                splits = $splits; has_data_yaml = (Test-Path -LiteralPath (Join-Path $extract 'data.yaml'))
                long_filenames_shortened = $renamedNames
                readme_licence_lines = $readmeLicence
            }
        }
    }

    [IO.File]::WriteAllText((Join-Path $entryDir 'metadata.json'), ($record | ConvertTo-Json -Depth 10))
    $summaries += [pscustomobject]$record
    $classText = ($classes | ForEach-Object { "$($_.name):$($_.count)" }) -join ', '
    Write-Output "$($e.name): type=$($p.type) images=$($p.images) versions=$($versions.Count) classes=[$classText]"
}

$reportDir = Join-Path $root 'reports/public-datasets'
[IO.Directory]::CreateDirectory($reportDir) | Out-Null
$reportPath = Join-Path $reportDir ('roboflow-' + $runStamp.ToString('yyyyMMdd-HHmmss') + '.json')
[IO.File]::WriteAllText($reportPath, (ConvertTo-Json -InputObject @($summaries) -Depth 10))
Write-Output "Saved Roboflow summary to $reportPath"
