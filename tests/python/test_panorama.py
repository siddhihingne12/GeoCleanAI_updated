import importlib
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import detector, providers
from backend.cache import cache
from backend.errors import ServiceError
from backend.geometry import point_to_basic
from backend.panorama import merge_detections, panorama_views, reproject_box

app_module = importlib.import_module('backend.app')
client = TestClient(app_module.app)


@pytest.fixture
def configured_panorama(monkeypatch):
    info = {'version': 'TEST-ONLY', 'sha256': 'a' * 64, 'confidence_threshold': .35}
    calls = {'download': 0, 'detect': 0}
    monkeypatch.setattr(detector, 'manifest', lambda: info)
    monkeypatch.setattr(providers, 'get_image', lambda *a, **k: ({'id': '123'}, {'captured_at': 123456}))

    def download(_item):
        calls['download'] += 1
        return Image.new('RGB', (128, 64))

    def detect(_crop, view, _info):
        calls['detect'] += 1
        return [{'id': 'litter-1', 'label': 'litter', 'confidence': .8,
                 'box': [.4, .4, .6, .6], 'tag': point_to_basic(.5, .5, view)}]

    monkeypatch.setattr(providers, 'download_panorama', download)
    monkeypatch.setattr(detector, 'detect', detect)
    return calls, info


def test_whole_sphere_is_covered_by_six_valid_views():
    views = panorama_views()
    assert len(views) == 6
    for longitude in np.linspace(-np.pi, np.pi, 37):
        for latitude in np.linspace(-np.pi / 2, np.pi / 2, 19):
            ray = np.array([np.cos(latitude) * np.sin(longitude), np.sin(latitude), np.cos(latitude) * np.cos(longitude)])
            visible = False
            for _name, view in views:
                depth = ray @ view.origin
                if depth <= 0:
                    continue
                right, down = np.array(view.right), np.array(view.down)
                visible |= abs(ray @ right / depth / (right @ right)) <= 1 and abs(ray @ down / depth / (down @ down)) <= 1
            assert visible


def test_overlap_suppression_keeps_distinct_objects_and_correct_evidence():
    views = dict(panorama_views())
    front_box = [.86, .48, .94, .60]
    right_box = reproject_box(front_box, views['front'], views['right'])
    detections = [
        {'view_id': 'front', 'box': front_box, 'confidence': .9, 'label': 'litter'},
        {'view_id': 'right', 'box': right_box, 'confidence': .8, 'label': 'litter'},
        {'view_id': 'right', 'box': [.45, .6, .5, .65], 'confidence': .7, 'label': 'litter'},
        {'view_id': 'back', 'box': [.49, .5, .52, .55], 'confidence': .6, 'label': 'litter'},
    ]
    result = merge_detections(detections, views)
    assert len(result) == 3
    assert result[0]['view_id'] == 'front'
    assert len({d['id'] for d in result}) == 3
    for d in result:
        x1, y1, x2, y2 = d['box']
        assert d['tag'] == pytest.approx(point_to_basic((x1 + x2) / 2, (y1 + y2) / 2, views[d['view_id']]))
    assert result[-1]['tag'][0] < .01  # Panorama seam stays wrapped, not mirrored.


def test_all_views_download_once_and_cached_reopening(configured_panorama):
    calls, _info = configured_panorama
    response = client.post('/api/analyze-panorama', json={'image_id': '123'})
    assert response.status_code == 200
    result = response.json()
    assert len(result['views']) == 6
    assert len(result['detections']) == 6
    assert len({d['id'] for d in result['detections']}) == 6
    assert {d['view_id'] for d in result['detections']} == {v['id'] for v in result['views']}
    assert all(v['preview'].startswith('data:image/jpeg;base64,') for v in result['views'])
    assert result['captured_at'] == 123456
    assert result['cached'] is False
    second = client.post('/api/analyze-panorama', json={'image_id': '123'}).json()
    assert second['cached'] is True
    assert second['detections'] == result['detections']
    assert calls == {'download': 1, 'detect': 6}


def test_existing_single_view_endpoint_remains_compatible(configured_panorama):
    calls, _info = configured_panorama
    view = panorama_views()[0][1].model_dump(mode='json')
    response = client.post('/api/analyze', json={'image_id': '123', 'view': view})
    assert response.status_code == 200
    body = response.json()
    assert body['view'] == view
    assert len(body['detections']) == 1
    assert 'view_id' not in body['detections'][0]
    assert body['preview'].startswith('data:image/jpeg;base64,')
    assert calls == {'download': 1, 'detect': 1}


@pytest.mark.parametrize('change', ['model', 'threshold', 'analysis', 'tiling'])
def test_cache_invalidated_by_analysis_inputs(configured_panorama, monkeypatch, change):
    calls, info = configured_panorama
    assert client.post('/api/analyze-panorama', json={'image_id': '123'}).status_code == 200
    if change == 'model':
        info['sha256'] = 'b' * 64
    elif change == 'threshold':
        info['confidence_threshold'] = .6
    elif change == 'analysis':
        import backend.panorama as panorama_module
        monkeypatch.setattr(panorama_module, 'ANALYSIS_VERSION', 'test-v2')
    else:
        info['tiling'] = {'face_size': 1024, 'tile': 640, 'stride': 384}
    result = client.post('/api/analyze-panorama', json={'image_id': '123'}).json()
    assert result['cached'] is False
    assert calls['download'] == 2


def test_failed_face_never_returns_or_caches_partial_results(configured_panorama, monkeypatch):
    original = detector.detect
    calls = 0

    def fail(_crop, view, info):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise ServiceError('inference_failed', 'Test failure')
        return original(_crop, view, info)

    monkeypatch.setattr(detector, 'detect', fail)
    failed = client.post('/api/analyze-panorama', json={'image_id': '123'})
    assert failed.status_code == 503
    assert 'detections' not in failed.json()
    assert not any(k.startswith('panorama-analysis:') for k in cache._data)
    monkeypatch.setattr(detector, 'detect', original)
    retried = client.post('/api/analyze-panorama', json={'image_id': '123'}).json()
    assert retried['cached'] is False
    assert len(retried['views']) == 6


def test_processing_deadline_returns_retryable_error_without_partial_cache(configured_panorama, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(app_module, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    original = detector.detect

    def slow(*args):
        clock[0] += 16
        return original(*args)

    monkeypatch.setattr(detector, 'detect', slow)
    result = client.post('/api/analyze-panorama', json={'image_id': '123'})
    assert result.status_code == 504
    assert result.json()['error']['code'] == 'analysis_timeout'
    assert not any(k.startswith('panorama-analysis:') for k in cache._data)


def test_panorama_respects_shared_inference_lease(configured_panorama):
    with cache.lease('inference'):
        result = client.post('/api/analyze-panorama', json={'image_id': '123'})
    assert result.status_code == 429
    assert result.headers['retry-after'] == '3'


def test_missing_model_is_not_an_empty_success():
    result = client.post('/api/analyze-panorama', json={'image_id': '123'})
    assert result.status_code == 503
    assert result.json()['error']['code'] == 'model_not_ready'
    assert 'detections' not in result.json()


@pytest.mark.parametrize('body', [{'image_id': 'https://example.org'}, {'image_id': '123', 'view': {}}, {}])
def test_panorama_request_validation(body):
    assert client.post('/api/analyze-panorama', json=body).status_code == 422


def test_tiled_model_gets_larger_views_and_small_previews(configured_panorama, monkeypatch):
    calls, info = configured_panorama
    info['tiling'] = {'face_size': 1024, 'tile': 640, 'stride': 384}
    sizes = []
    original = detector.detect
    monkeypatch.setattr(detector, 'detect', lambda crop, view, i: sizes.append(crop.size) or original(crop, view, i))
    body = client.post('/api/analyze-panorama', json={'image_id': '123'}).json()
    assert sizes == [(1024, 1024)] * 6
    assert body['analysis_version'].endswith('-tile1024-640s384')
    import base64, io
    preview = Image.open(io.BytesIO(base64.b64decode(body['views'][0]['preview'].split(',', 1)[1])))
    assert preview.size == (640, 640)
