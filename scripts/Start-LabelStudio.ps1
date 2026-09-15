param([int]$Port = 8080)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$exe = Join-Path $root '.venv\Scripts\label-studio.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Label Studio is not installed. Run: .venv\Scripts\python.exe -m pip install label-studio' }

# Images are served straight from this workspace, so task URLs in the import files are
# repository-relative. Label Studio also requires a "Local files" source storage in each
# project whose path covers the images (see reports/labelling/README.md).
$env:LOCAL_FILES_SERVING_ENABLED = 'true'
$env:LOCAL_FILES_DOCUMENT_ROOT = $root
# Keep the annotation database with the other git-ignored data.
$env:LABEL_STUDIO_BASE_DATA_DIR = Join-Path $root 'data\label-studio'

# Bind to this computer only; the default listens on every network interface.
& $exe start --internal-host localhost --port $Port
