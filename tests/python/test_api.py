import json
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.cache import cache
from backend import providers
from backend.errors import ServiceError

client = TestClient(app)
CAMERA = {'origin': [0,0,1], 'right': [1,0,0], 'down': [0,-1,0], 'aspect': 1}

def test_health_does_not_claim_ready_without_model_or_token():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'setup_required'
    assert response.json()['checks']['model'] is False
    assert response.json()['samples'] == []

def test_missing_model_never_returns_fake_empty_detection():
    response = client.post('/api/analyze', json={'image_id': '123', 'view': CAMERA})
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'model_not_ready'
    assert 'detections' not in response.json()

@pytest.mark.parametrize('payload', [{'image_id': 'https://evil.test', 'view': CAMERA}, {'image_id': '123', 'view': {**CAMERA, 'aspect': 0}}, {'image_id': '123', 'view': CAMERA, 'url': 'http://localhost'}])
def test_input_validation(payload):
    assert client.post('/api/analyze', json=payload).status_code == 422

def test_outside_pune_is_rejected():
    assert client.get('/api/panoramas?lat=19.07&lng=72.87').status_code == 422

def test_local_cache_forbidden_in_vercel(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    assert not cache.configured
    with pytest.raises(ServiceError, match='Upstash'):
        cache.get('some-key')

def test_lease_is_atomic_and_ownership_safe():
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda n: cache.reserve('slot', str(n), 5000), range(10)))
    assert sum(results) == 1
    winner = results.index(True)
    cache.release('slot', 'wrong-owner')
    assert not cache.reserve('slot', 'new', 5000)
    cache.release('slot', str(winner))
    assert cache.reserve('slot', 'new', 5000)

def test_search_cache_avoids_upstream_and_global_throttle(monkeypatch):
    monkeypatch.setenv('NOMINATIM_USER_AGENT', 'GeoCleanAI-test/1.0 (https://example.org/project)')
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, json=[{'place_id': '1', 'display_name': 'Pune', 'lat': '18.52', 'lon': '73.85'}], request=httpx.Request('GET', url))
    monkeypatch.setattr(httpx, 'get', get)
    assert client.get('/api/search?q=Pune').status_code == 200
    assert client.get('/api/search?q=Pune').status_code == 200
    assert len(calls) == 1
    assert client.get('/api/search?q=Kothrud').status_code == 429
    assert calls[0]['params']['bounded'] == 1

def test_metadata_filters_panorama_and_service_area(monkeypatch):
    raw = {'id': '123', 'geometry': {'coordinates': [73.85,18.52]}, 'is_pano': False}
    monkeypatch.setattr(providers, 'graph', lambda *_args, **_kwargs: raw)
    with pytest.raises(ServiceError) as exc:
        providers.get_image('123')
    assert exc.value.code == 'not_panorama'

def test_download_rejects_arbitrary_or_local_urls():
    for url in ['http://127.0.0.1/foo', 'https://fbcdn.net.evil.test/image', 'https://example.com/image']:
        with pytest.raises(ServiceError) as exc:
            providers.download_panorama({'thumb_original_url': url})
        assert exc.value.code == 'image_host_invalid'

def test_graph_failure_does_not_leak_tokens(monkeypatch):
    monkeypatch.setenv('MAPILLARY_ACCESS_TOKEN', 'secret-test-value')
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: httpx.Response(403, request=httpx.Request('GET', 'https://graph.mapillary.com')))
    response = client.get('/api/panoramas/123')
    assert response.status_code == 502
    assert 'secret-test-value' not in response.text
