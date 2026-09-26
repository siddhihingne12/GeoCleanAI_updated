import pytest
from backend.cache import cache

@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setenv('ALLOW_LOCAL_CACHE', '1')
    monkeypatch.delenv('UPSTASH_REDIS_REST_URL', raising=False)
    monkeypatch.delenv('UPSTASH_REDIS_REST_TOKEN', raising=False)
    monkeypatch.setenv('MAPILLARY_ACCESS_TOKEN', '')
    monkeypatch.setenv('MODEL_PATH', str(tmp_path / 'missing.onnx'))
    monkeypatch.setenv('MODEL_MANIFEST_PATH', str(tmp_path / 'missing.json'))
    cache._data.clear()
