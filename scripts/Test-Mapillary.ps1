param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
$mapillaryToken = $null
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*MAPILLARY_TOKEN\s*=\s*(.*?)\s*$') {
            $mapillaryToken = $Matches[1].Trim().Trim('"').Trim("'")
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($mapillaryToken) -or $mapillaryToken -eq 'PASTE_CLIENT_TOKEN_HERE') {
    $mapillaryToken = [Environment]::GetEnvironmentVariable('MAPILLARY_TOKEN')
}
if ([string]::IsNullOrWhiteSpace($mapillaryToken)) {
    Write-Output 'SETUP NEEDED: Paste the complete Mapillary Client Token after MAPILLARY_TOKEN= in the project .env file.'
    exit 2
}
if ($mapillaryToken -match '\s' -or $mapillaryToken -notmatch '^MLY\|') {
    Write-Output 'SETUP NEEDED: Use the complete Client Token from the Mapillary developer dashboard, without an OAuth prefix or spaces.'
    exit 2
}
if ($CheckOnly) {
    Write-Output 'Token is configured. Its validity has not been checked with Mapillary.'
    exit 0
}

$requestUri = 'https://graph.mapillary.com/images?bbox=73.770,18.650,73.772,18.652&limit=5&fields=id,geometry'
try {
    $response = Invoke-RestMethod -Uri $requestUri -Headers @{ Authorization = "OAuth $mapillaryToken" } -TimeoutSec 30 -ErrorAction Stop
    $images = @($response.data | Where-Object { $null -ne $_ })
    Write-Output "Connection succeeded. This small test area returned $($images.Count) image(s)."
    if ($images.Count -gt 0) {
        $images | Select-Object id, geometry | ConvertTo-Json -Depth 5
    } else {
        Write-Output 'An empty result does not establish coverage for the wider corridor.'
    }
} catch {
    # Never print request headers, token values, or raw response bodies.
    $apiErrorCode = $null
    try {
        $errorBody = $_.ErrorDetails.Message | ConvertFrom-Json
        $apiErrorCode = [int]$errorBody.error.code
    } catch { }
    switch ($apiErrorCode) {
        190 { Write-Output 'Mapillary rejected the token (code 190). Replace the value in .env with the complete Client Token.' }
        1 { Write-Output 'Mapillary could not complete this query (code 1). A smaller query or a later retry may be needed.' }
        default { Write-Output 'Connection failed. Check network access and Mapillary availability. Request details were withheld to protect the token.' }
    }
    exit 1
}
