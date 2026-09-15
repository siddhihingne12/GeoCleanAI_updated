param(
    [Parameter(Mandatory = $true)]
    [string]$Folder,
    # Short identifier used for the report name, e.g. qr4change_dumps.
    [Parameter(Mandatory = $true)]
    [string]$Name,
    # Difference-hash Hamming distance (of 64 bits) at or below which two photos are near-duplicates.
    [int]$MaxHashDistance = 10,
    # Photos taken this close in time are one capture session...
    [int]$MaxSeconds = 90,
    # ...provided they are also this close in space when both carry GPS.
    [double]$MaxMetres = 30
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-z0-9_]+$') { throw 'Name must be a simple lowercase identifier.' }
$root = Split-Path $PSScriptRoot -Parent
$source = $Folder
if (-not [IO.Path]::IsPathRooted($source)) { $source = Join-Path $root $Folder }
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw "Folder not found: $Folder" }
$source = (Resolve-Path -LiteralPath $source).Path.TrimEnd('\')
$culture = [Globalization.CultureInfo]::InvariantCulture

# Hashing and the all-pairs comparison run in C#: in plain PowerShell a quarter of a
# million pair checks take minutes rather than seconds.
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Text;

public static class GeoCleanImageKeys {
    public static ulong DHash(Image img) {
        using (var small = new Bitmap(9, 8, PixelFormat.Format24bppRgb))
        using (var g = Graphics.FromImage(small)) {
            g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBilinear;
            g.DrawImage(img, 0, 0, 9, 8);
            ulong hash = 0; int bit = 0;
            for (int y = 0; y < 8; y++) {
                for (int x = 0; x < 8; x++) {
                    Color a = small.GetPixel(x, y), b = small.GetPixel(x + 1, y);
                    double la = 0.299 * a.R + 0.587 * a.G + 0.114 * a.B;
                    double lb = 0.299 * b.R + 0.587 * b.G + 0.114 * b.B;
                    if (la > lb) hash |= (1UL << bit);
                    bit++;
                }
            }
            return hash;
        }
    }

    static int Distance(ulong a, ulong b) { ulong v = a ^ b; int c = 0; while (v != 0) { v &= v - 1; c++; } return c; }

    static double Rational(byte[] v, int offset) {
        uint n = BitConverter.ToUInt32(v, offset); uint d = BitConverter.ToUInt32(v, offset + 4);
        return d == 0 ? 0 : (double)n / d;
    }

    // EXIF GPS: value tag holds degrees, minutes, seconds as rationals; reference tag holds N/S or E/W.
    public static double Coordinate(Image img, int valueId, int refId) {
        try {
            var p = img.GetPropertyItem(valueId); var r = img.GetPropertyItem(refId);
            double deg = Rational(p.Value, 0) + Rational(p.Value, 8) / 60.0 + Rational(p.Value, 16) / 3600.0;
            string rs = Encoding.ASCII.GetString(r.Value).Trim('\0', ' ');
            if (rs == "S" || rs == "W") deg = -deg;
            return deg == 0 ? double.NaN : deg;
        } catch { return double.NaN; }
    }

    public static string TakenAt(Image img) {
        foreach (int id in new[] { 0x9003, 0x0132 }) {
            try { return Encoding.ASCII.GetString(img.GetPropertyItem(id).Value).Trim('\0', ' '); } catch { }
        }
        return null;
    }

    static double Metres(double lat1, double lon1, double lat2, double lon2) {
        double rad = Math.PI / 180, dlat = (lat2 - lat1) * rad, dlon = (lon2 - lon1) * rad;
        double h = Math.Pow(Math.Sin(dlat / 2), 2) + Math.Cos(lat1 * rad) * Math.Cos(lat2 * rad) * Math.Pow(Math.Sin(dlon / 2), 2);
        return 6371000 * 2 * Math.Asin(Math.Sqrt(Math.Min(1.0, h)));
    }

    static int Find(int[] parent, int i) {
        while (parent[i] != i) { parent[i] = parent[parent[i]]; i = parent[i]; }
        return i;
    }

    static void Union(int[] parent, int i, int j) {
        int a = Find(parent, i), b = Find(parent, j);
        if (a != b) parent[b] = a;
    }

    // Union-find over two link types. Returns the root index for every photo.
    // ticks < 0 means no capture time; NaN latitude means no GPS.
    // Time links join only photos that are adjacent in capture order. Linking every pair
    // inside a time window chains a whole burst-shot survey ride into one group: QR4Change
    // shot 610 photos in an hour with a median one-second gap and no GPS.
    public static int[] Group(ulong[] hashes, long[] ticks, double[] lat, double[] lon,
                              int maxHash, int maxSeconds, double maxMetres, out int visualLinks, out int sessionLinks) {
        int n = hashes.Length; var parent = new int[n];
        for (int i = 0; i < n; i++) parent[i] = i;
        visualLinks = 0; sessionLinks = 0;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (Distance(hashes[i], hashes[j]) <= maxHash) { visualLinks++; Union(parent, i, j); }
            }
        }
        long maxTicks = TimeSpan.FromSeconds(maxSeconds).Ticks;
        var timed = new System.Collections.Generic.List<int>();
        for (int i = 0; i < n; i++) if (ticks[i] >= 0) timed.Add(i);
        timed.Sort((a, b) => ticks[a].CompareTo(ticks[b]));
        for (int k = 1; k < timed.Count; k++) {
            int i = timed[k - 1], j = timed[k];
            if (ticks[j] - ticks[i] > maxTicks) continue;
            bool bothGps = !double.IsNaN(lat[i]) && !double.IsNaN(lat[j]);
            if (!bothGps || Metres(lat[i], lon[i], lat[j], lon[j]) <= maxMetres) { sessionLinks++; Union(parent, i, j); }
        }
        var roots = new int[n];
        for (int i = 0; i < n; i++) roots[i] = Find(parent, i);
        return roots;
    }
}
"@

$files = @(Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object { $_.Extension -match '^\.(jpe?g|png)$' } | Sort-Object FullName)
if ($files.Count -lt 2) { throw 'Need at least two images to group.' }
Write-Output "Hashing $($files.Count) images under $source."

$items = New-Object System.Collections.Generic.List[object]
foreach ($f in $files) {
    $hash = [uint64]0; $lat = [double]::NaN; $lon = [double]::NaN; $taken = $null; $readable = $true
    try {
        $stream = [IO.File]::OpenRead($f.FullName)
        try {
            $img = [Drawing.Image]::FromStream($stream, $false, $false)
            try {
                $hash = [GeoCleanImageKeys]::DHash($img)
                $lat = [GeoCleanImageKeys]::Coordinate($img, 2, 1)
                $lon = [GeoCleanImageKeys]::Coordinate($img, 4, 3)
                $taken = [GeoCleanImageKeys]::TakenAt($img)
            } finally { $img.Dispose() }
        } finally { $stream.Dispose() }
    } catch { $readable = $false }
    $time = $null
    if ($taken) {
        $parsed = [DateTime]::MinValue
        if ([DateTime]::TryParseExact($taken, 'yyyy:MM:dd HH:mm:ss', $culture, [Globalization.DateTimeStyles]::None, [ref]$parsed)) { $time = $parsed }
    }
    if ($readable) {
        $items.Add([pscustomobject]@{
            file = $f.FullName.Substring($source.Length).TrimStart('\'); hash = $hash; lat = $lat; lon = $lon; time = $time
        })
    } else {
        Write-Output "Unreadable, skipped: $($f.Name)"
    }
    if ($items.Count % 100 -eq 0) { Write-Output "Hashed $($items.Count) of $($files.Count)" }
}

$n = $items.Count
$hashes = New-Object 'uint64[]' $n; $ticks = New-Object 'int64[]' $n
$lats = New-Object 'double[]' $n; $lons = New-Object 'double[]' $n
for ($i = 0; $i -lt $n; $i++) {
    $hashes[$i] = $items[$i].hash; $lats[$i] = $items[$i].lat; $lons[$i] = $items[$i].lon
    $ticks[$i] = -1
    if ($null -ne $items[$i].time) { $ticks[$i] = $items[$i].time.Ticks }
}
$visual = 0; $session = 0
$roots = [GeoCleanImageKeys]::Group($hashes, $ticks, $lats, $lons, $MaxHashDistance, $MaxSeconds, $MaxMetres, [ref]$visual, [ref]$session)

$groupIds = @{}
$groups = @(0..($n - 1) | Group-Object { $roots[$_] } | Sort-Object Count -Descending | ForEach-Object {
    $members = @($_.Group | ForEach-Object { $items[[int]$_] })
    $id = 'g{0:D4}' -f ($groupIds.Count + 1)
    foreach ($m in $_.Group) { $groupIds[[int]$m] = $id }
    $withGps = @($members | Where-Object { -not [double]::IsNaN($_.lat) })
    $withTime = @($members | Where-Object { $null -ne $_.time } | Sort-Object time)
    $centroid = $null
    if ($withGps.Count -gt 0) {
        $centroid = @(
            [Math]::Round(($withGps | Measure-Object lat -Average).Average, 6),
            [Math]::Round(($withGps | Measure-Object lon -Average).Average, 6)
        )
    }
    [ordered]@{
        group = $id; size = $members.Count
        first_taken = $(if ($withTime.Count) { $withTime[0].time.ToString('s') } else { $null })
        last_taken = $(if ($withTime.Count) { $withTime[-1].time.ToString('s') } else { $null })
        gps_centroid_lat_lon = $centroid
        files = @($members | ForEach-Object { $_.file })
    }
})

$images = @(for ($i = 0; $i -lt $n; $i++) {
    $it = $items[$i]
    [ordered]@{
        file = $it.file; group = $groupIds[$i]; dhash = ('{0:x16}' -f $it.hash)
        taken = $(if ($null -ne $it.time) { $it.time.ToString('s') } else { $null })
        lat = $(if ([double]::IsNaN($it.lat)) { $null } else { [Math]::Round($it.lat, 6) })
        lon = $(if ([double]::IsNaN($it.lon)) { $null } else { [Math]::Round($it.lon, 6) })
    }
})
$gpsItems = @($items | Where-Object { -not [double]::IsNaN($_.lat) })
$sizes = @($groups | ForEach-Object { $_.size })
$report = [ordered]@{
    name = $Name; source_folder = $source; checked_at = [DateTimeOffset]::UtcNow.ToString('o')
    parameters = [ordered]@{ max_hash_distance = $MaxHashDistance; max_seconds = $MaxSeconds; max_metres = $MaxMetres }
    images = $n; with_capture_time = @($items | Where-Object { $null -ne $_.time }).Count; with_gps = $gpsItems.Count
    gps_bounds_west_south_east_north = $(if ($gpsItems.Count) { @(
        ($gpsItems | Measure-Object lon -Minimum).Minimum, ($gpsItems | Measure-Object lat -Minimum).Minimum,
        ($gpsItems | Measure-Object lon -Maximum).Maximum, ($gpsItems | Measure-Object lat -Maximum).Maximum) } else { $null })
    visual_links = $visual; session_links = $session
    groups = $groups.Count; singleton_groups = @($sizes | Where-Object { $_ -eq 1 }).Count
    largest_group_sizes = @($sizes | Select-Object -First 10)
    group_list = $groups; image_list = $images
}
$reportDir = Join-Path $root 'reports/public-datasets'
[IO.Directory]::CreateDirectory($reportDir) | Out-Null
$reportPath = Join-Path $reportDir "$Name-groups.json"
[IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 6))
Write-Output "Images: $n; with capture time: $($report.with_capture_time); with GPS: $($report.with_gps)"
Write-Output "Visual links: $visual; session links: $session"
Write-Output "Groups: $($groups.Count) ($($report.singleton_groups) singletons); largest: $(($report.largest_group_sizes) -join ', ')"
Write-Output "Saved grouping to $reportPath"
