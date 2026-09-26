import io
import math
import os
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from backend.cache import cache
from backend.config import PUNE_BOUNDS, in_pune, mapillary_token
from backend.errors import ServiceError

Image.MAX_IMAGE_PIXELS = 40_000_000
GRAPH = 'https://graph.mapillary.com'
FIELDS = 'id,geometry,captured_at,creator,is_pano,thumb_2048_url'

def graph(path: str, params: dict | None = None):
    if not mapillary_token():
        raise ServiceError('mapillary_not_configured', 'Add your Mapillary client access token to enable street imagery.')
    try:
        response = httpx.get(f'{GRAPH}/{path}', headers={'Authorization': f'OAuth {mapillary_token()}'}, params=params, timeout=15)
        if response.status_code == 429:
            raise ServiceError('provider_rate_limit', 'Mapillary is busy. Please try again later.', 429, 30)
        if response.status_code in (400, 401, 403):
            raise ServiceError('mapillary_request_failed', 'Mapillary could not serve this request. Check the token and image access.', 502)
        if response.status_code == 404:
            raise ServiceError('image_missing', 'This street photograph is no longer available.', 404)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise ServiceError('mapillary_unavailable', 'Could not reach Mapillary. Please retry.', 502) from None

def normalize_image(item: dict) -> dict:
    coords = (item.get('geometry') or {}).get('coordinates', [])
    if len(coords) != 2:
        raise ServiceError('image_metadata_missing', 'The photograph is missing its location.', 422)
    return {'id': str(item['id']), 'lng': coords[0], 'lat': coords[1], 'captured_at': item.get('captured_at') or 0, 'creator': (item.get('creator') or {}).get('username', 'Mapillary contributor'), 'is_pano': bool(item.get('is_pano')), 'thumbnail_url': item.get('thumb_2048_url')}

def get_image(image_id: str, original: bool = False):
    item = graph(image_id, {'fields': FIELDS + (',thumb_original_url' if original else '')})
    meta = normalize_image(item)
    if not in_pune(meta['lat'], meta['lng']):
        raise ServiceError('outside_pune', 'Choose an image inside the Pune demo area.', 422)
    if not meta['is_pano']:
        raise ServiceError('not_panorama', 'This photograph is not a panorama. Choose a 360° image.', 422)
    return item, meta

def distance_m(lat: float, lng: float, lat2: float, lng2: float):
    a, b = math.radians(lat), math.radians(lat2)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(lng2 - lng) / 2) ** 2
    return round(6_371_000 * 2 * math.asin(math.sqrt(min(1, h))))

def nearby(lat: float, lng: float):
    key = f'panoramas:{lat:.5f}:{lng:.5f}'
    existing = cache.get(key)
    if existing is not None:
        return existing
    radius = 500
    dx, dy = radius / (111_320 * math.cos(math.radians(lat))), radius / 111_320
    west, south, east, north = PUNE_BOUNDS
    bbox = f'{max(west,lng-dx)},{max(south,lat-dy)},{min(east,lng+dx)},{min(north,lat+dy)}'
    raw = graph('images', {'bbox': bbox, 'is_pano': 'true', 'fields': FIELDS, 'limit': 100})
    items = []
    for row in raw.get('data', []):
        meta = normalize_image(row)
        distance = distance_m(lat, lng, meta['lat'], meta['lng'])
        if meta['is_pano'] and in_pune(meta['lat'], meta['lng']) and distance <= radius:
            items.append({**meta, 'distance_m': distance})
    result = {'panoramas': sorted(items, key=lambda row: (row['distance_m'], -row['captured_at'])), 'truncated': bool(raw.get('paging', {}).get('next'))}
    cache.put(key, result, 600)
    return result

def search(query: str):
    key = f'search:{query.casefold().strip()}'
    existing = cache.get(key)
    if existing is not None:
        return existing
    agent = os.getenv('NOMINATIM_USER_AGENT', '')
    if not agent or 'replace-with' in agent:
        raise ServiceError('search_not_configured', 'Set a project URL or contact in NOMINATIM_USER_AGENT to enable place search. Map selection still works.')
    # Starts are separated globally by >= 1100ms, including across function instances.
    if not cache.reserve('nominatim:interval', 'reserved', 1100):
        raise ServiceError('search_busy', 'Please wait a moment before searching again.', 429, 2)
    west, south, east, north = PUNE_BOUNDS
    try:
        response = httpx.get(os.getenv('NOMINATIM_URL', 'https://nominatim.openstreetmap.org/search'), params={'q': query, 'format': 'jsonv2', 'countrycodes': 'in', 'viewbox': f'{west},{north},{east},{south}', 'bounded': 1, 'limit': 6}, headers={'User-Agent': agent}, timeout=12)
        response.raise_for_status()
        result = {'places': [{'id': str(p['place_id']), 'name': p['display_name'], 'lat': float(p['lat']), 'lng': float(p['lon'])} for p in response.json() if in_pune(float(p['lat']), float(p['lon']))]}
    except (httpx.HTTPError, ValueError, KeyError):
        raise ServiceError('search_unavailable', 'Place search is temporarily unavailable. Select a point on the map instead.', 502) from None
    cache.put(key, result, 86400)
    return result

def download_panorama(item: dict) -> Image.Image:
    url = item.get('thumb_original_url') or item.get('thumb_2048_url')
    if not url:
        raise ServiceError('image_missing', 'The panorama image is unavailable.', 404)
    parsed = urlparse(url)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not any(host == domain or host.endswith('.' + domain) for domain in ('fbcdn.net', 'fbsbx.com', 'mapillary.com')):
        raise ServiceError('image_host_invalid', 'Mapillary returned an unsupported image location.', 502)
    content = bytearray()
    try:
        with httpx.stream('GET', url, timeout=20, follow_redirects=False) as response:
            response.raise_for_status()
            for block in response.iter_bytes():
                content.extend(block)
                if len(content) > 24 * 1024 * 1024:
                    raise ServiceError('image_too_large', 'This panorama is too large for the demo. Choose a nearby image.', 422)
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        if image.width * image.height > 40_000_000 or abs(image.width / image.height - 2) > .06:
            raise ServiceError('unsupported_panorama', 'This panorama is not a supported full spherical image.', 422)
        image.load()
        return image.convert('RGB')
    except (httpx.HTTPError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ServiceError('image_download_failed', 'Could not load this panorama for analysis. Try a nearby photograph.', 502) from None
