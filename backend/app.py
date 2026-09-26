import hashlib
import json
import logging
import os
import time

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from backend import detector, providers
from backend.cache import cache
from backend.config import ROOT, in_pune, mapillary_token
from backend.errors import ServiceError
from backend.geometry import perspective, preview_data_url
from backend.panorama import analysis_version, merge_detections, panorama_views
from backend.schemas import AnalysisRequest, PanoramaAnalysisRequest

app = FastAPI(title='GeoCleanAI', version='0.1.0', docs_url='/api/docs', openapi_url='/api/openapi.json')
logger = logging.getLogger('geoclean')

@app.exception_handler(ServiceError)
async def service_error(_request: Request, exc: ServiceError):
    headers = {'Retry-After': str(exc.retry_after)} if exc.retry_after else {}
    return JSONResponse(status_code=exc.status, content={'error': {'code': exc.code, 'message': exc.message}}, headers=headers)

@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {'code': 'invalid_request', 'message': 'Check the location or viewing direction and try again.'}})

@app.middleware('http')
async def timing(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    logger.info('%s %s status=%s duration_ms=%d', request.method, request.url.path, response.status_code, round((time.monotonic()-start)*1000))
    return response

@app.get('/api/health')
def health():
    try:
        info = detector.manifest()
    except ServiceError:
        info = None
    agent = os.getenv('NOMINATIM_USER_AGENT', '')
    checks = {'mapillary': bool(mapillary_token()), 'shared_cache': cache.configured, 'model': info is not None, 'search': bool(agent) and 'replace-with' not in agent}
    try:
        samples = json.loads((ROOT / 'public' / 'samples.json').read_text())
    except (OSError, ValueError):
        samples = []
    return {'status': 'ready' if all(checks.values()) else 'setup_required', 'checks': checks, 'model_version': info['version'] if info else None, 'samples': samples}

@app.get('/api/search')
def search(q: str = Query(min_length=2, max_length=150)):
    return providers.search(q.strip())

@app.get('/api/panoramas')
def panoramas(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180)):
    if not in_pune(lat, lng):
        raise ServiceError('outside_pune', 'Select a location inside the Pune demo area.', 422)
    return providers.nearby(lat, lng)

@app.get('/api/panoramas/{image_id}')
def panorama(image_id: str):
    if not image_id.isdigit() or len(image_id) > 30:
        raise ServiceError('invalid_image_id', 'Choose a valid street photograph.', 422)
    _, meta = providers.get_image(image_id)
    return meta

@app.post('/api/analyze')
def analyze(body: AnalysisRequest):
    started = time.monotonic()
    info = detector.manifest()
    digest = hashlib.sha256(json.dumps({'image_id': body.image_id, 'view': body.view.model_dump(), 'sha': info['sha256'], 'threshold': info.get('confidence_threshold', .35), 'analysis_version': analysis_version(info)}, sort_keys=True).encode()).hexdigest()
    key = f'analysis:{digest}'
    existing = cache.get(key)
    if existing is not None:
        return {**existing, 'cached': True, 'elapsed_ms': round((time.monotonic()-started)*1000)}
    with cache.lease('inference'):
        # A single globally coordinated slot suits a small, free college demo.
        item, meta = providers.get_image(body.image_id, original=True)
        source = providers.download_panorama(item)
        crop = perspective(source, body.view, longest_side=detector.view_size(info))
        source.close()
        detections = detector.detect(crop, body.view, info)
        result = {'image_id': body.image_id, 'model_version': info['version'], 'detections': detections, 'view': body.view.model_dump(), 'preview': preview_data_url(crop), 'captured_at': meta['captured_at'], 'cached': False, 'elapsed_ms': round((time.monotonic()-started)*1000)}
        crop.close()
        cache.put(key, result, 86400)
        return result


@app.post('/api/analyze-panorama')
def analyze_panorama(body: PanoramaAnalysisRequest):
    started = time.monotonic()
    info = detector.manifest()
    digest = hashlib.sha256(json.dumps({
        'image_id': body.image_id, 'sha': info['sha256'],
        'threshold': info.get('confidence_threshold', .35), 'analysis_version': analysis_version(info),
    }, sort_keys=True).encode()).hexdigest()
    key = f'panorama-analysis:{digest}'

    def cached_result():
        existing = cache.get(key)
        return None if existing is None else {**existing, 'cached': True, 'elapsed_ms': round((time.monotonic() - started) * 1000)}

    def check_deadline():
        # Leave time for cache writes, response serialization and lease release.
        if time.monotonic() - started > 45:
            raise ServiceError('analysis_timeout', 'Litter detection took too long. Please retry or choose another photograph.', 504)

    existing = cached_result()
    if existing is not None:
        return existing
    with cache.lease('inference'):
        existing = cached_result()
        if existing is not None:
            return existing
        item, meta = providers.get_image(body.image_id, original=True)
        check_deadline()
        views = panorama_views()
        previews, detections = [], []
        with providers.download_panorama(item) as source:
            for view_id, view in views:
                check_deadline()
                with perspective(source, view, longest_side=detector.view_size(info)) as crop:
                    detections.extend({**d, 'view_id': view_id} for d in detector.detect(crop, view, info))
                    previews.append({'id': view_id, 'view': view.model_dump(), 'preview': preview_data_url(crop)})
        check_deadline()
        result = {
            'image_id': body.image_id, 'model_version': info['version'], 'analysis_version': analysis_version(info),
            'detections': merge_detections(detections, dict(views)), 'views': previews,
            'captured_at': meta['captured_at'], 'cached': False,
            'elapsed_ms': round((time.monotonic() - started) * 1000),
        }
        check_deadline()
        # Never save or return partially analysed panoramas.
        cache.put(key, result, 86400)
        return result
