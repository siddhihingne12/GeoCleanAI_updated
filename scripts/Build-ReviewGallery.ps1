param(
    [string]$ReviewFolder = 'reports/visual-review/candidate-b',
    [string]$Heading = 'Area B: sample review',
    [string]$ReviewDate = (Get-Date -Format 'd MMMM yyyy'),
    [string]$Summary = '<strong>Decision: hold full annotation.</strong><p>27 images inspected across all 9 sequences. No clear roadside dump or overflowing bin was identified at the downloaded review resolution. Four images are useful candidates for difficult negative examples. This does not prove that the full area contains no waste.</p><p>24 panoramas and 3 perspective images. Click a photo to inspect its full downloaded size. These are preliminary review notes, not training labels or model predictions.</p>'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$folder = Join-Path $root $ReviewFolder
$manifest = Get-Content -Raw -LiteralPath (Join-Path $folder 'manifest.json') | ConvertFrom-Json
$notes = Get-Content -Raw -LiteralPath (Join-Path $folder 'review-notes.json') | ConvertFrom-Json
function Encode($value) { [Net.WebUtility]::HtmlEncode([string]$value) }
# Every downloaded sample must carry exactly one review note: an unreviewed frame in the
# gallery would read as inspected when it was not.
if ($manifest.Count -lt 1) { throw 'Manifest is empty.' }
if ($manifest.Count -ne $notes.Count) { throw "Expected one review note per sample; found $($manifest.Count) samples and $($notes.Count) notes." }
$cards = foreach ($row in $manifest) {
    $note = @($notes | Where-Object { $_.image_id -eq $row.image_id })
    if ($note.Count -ne 1 -or $row.status -ne 'downloaded') { throw 'Missing review or download.' }
    if (-not (Test-Path -LiteralPath (Join-Path $folder $row.file))) { throw 'Missing image file.' }
    $tag = switch ($note[0].finding) {
        'roadside_dump_positive' { 'Roadside dump: clear positive' }
        'roadside_dump_candidate' { 'Roadside dump candidate, needs confirmation' }
        'overflowing_bin_positive' { 'Overflowing bin: clear positive' }
        'hard_negative_candidate' { 'Potential negative example' }
        'limited_visibility' { 'Visibility limited' }
        'weak_positive_accumulation' { 'Weak accumulation, below label threshold' }
        'uncertain_scattered_litter' { 'Scattered litter, uncertain' }
        'unusable_camera_aim' { 'Unusable: camera aim' }
        'unusable_quality' { 'Unusable: image quality' }
        'unusable_occlusion' { 'Unusable: occlusion' }
        default { 'No clear target observed' }
    }
    @"
<article>
<a href="$(Encode $row.file)"><img loading="lazy" src="$(Encode $row.file)" alt="Mapillary street image $(Encode $row.image_id)"></a>
<div class="body"><span class="tag">$(Encode $tag)</span><h2>$(Encode $row.image_id)</h2>
<p>$(Encode $note[0].note)</p>
<p class="meta">Capture metadata: $(Encode $row.captured_at.Substring(0,10)) · $(Encode $row.camera_type)<br>Sequence: $(Encode $row.sequence_id)</p>
<p class="meta">Imagery: Mapillary contributor $(Encode $row.creator.username). <a href="$(Encode $row.mapillary_url)">View source and contributor attribution</a>.</p>
</div></article>
"@
}
$html = @"
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoClean AI V2 - $(Encode $Heading)</title>
<style>
body{margin:0;background:#f4f6f5;color:#18332c;font:16px/1.6 system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:36px 24px}h1{font-size:32px;line-height:1.2}h2{font-size:17px;overflow-wrap:anywhere}.summary{background:#fff;padding:24px;border-left:5px solid #ab6f12;border-radius:8px;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}article{background:#fff;border:1px solid #dce3df;border-radius:10px;overflow:hidden}img{width:100%;height:auto;display:block}.body{padding:20px}.tag{background:#eaf0ed;padding:5px 9px;border-radius:5px;font-size:13px}.meta{font-size:13px;color:#4a6058;overflow-wrap:anywhere}a{color:#146249}footer{margin-top:32px;font-size:14px}
</style></head><body><main>
<p>GEOCLEAN AI · MAPILLARY STREET-LEVEL METHOD V2</p><h1>$(Encode $Heading)</h1>
<div class="summary">$Summary</div>
<section class="grid">$($cards -join "`n")</section>
<footer>Review date: $(Encode $ReviewDate). Images remain attributed to their Mapillary contributors and linked to their original source. Source JPEGs were not edited. Keep sample images with their manifest and attribution.</footer>
</main></body></html>
"@
[IO.File]::WriteAllText((Join-Path $folder 'index.html'),$html)
Write-Output "PASS: all $($manifest.Count) downloaded samples have exactly one review note and a gallery entry."
Write-Output "Gallery saved to $folder/index.html"
