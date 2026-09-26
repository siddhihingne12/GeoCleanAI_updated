import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if not os.getenv('VERCEL'):
    load_dotenv(ROOT / '.env.local')

# Explicit demo service boundary; not a municipal-boundary claim.
PUNE_BOUNDS = (73.70, 18.40, 74.05, 18.70)

def in_pune(lat: float, lng: float) -> bool:
    west, south, east, north = PUNE_BOUNDS
    return south <= lat <= north and west <= lng <= east

def model_path() -> Path:
    return ROOT / os.getenv('MODEL_PATH', 'models/litter.onnx')

def manifest_path() -> Path:
    return ROOT / os.getenv('MODEL_MANIFEST_PATH', 'models/manifest.json')

def mapillary_token() -> str:
    return os.getenv('MAPILLARY_ACCESS_TOKEN', '')

def local_cache_allowed() -> bool:
    return not os.getenv('VERCEL') and os.getenv('ALLOW_LOCAL_CACHE') == '1'
