"""Redis-backed cache and leases. Local fallback is forbidden on Vercel."""
import json
import os
import threading
import time
from contextlib import contextmanager
from uuid import uuid4

import httpx
from backend.config import local_cache_allowed
from backend.errors import ServiceError

class Cache:
    def __init__(self):
        self._data: dict[str, tuple[float, str]] = {}
        self._mutex = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(os.getenv('UPSTASH_REDIS_REST_URL') and os.getenv('UPSTASH_REDIS_REST_TOKEN')) or local_cache_allowed()

    def command(self, *args):
        url, token = os.getenv('UPSTASH_REDIS_REST_URL'), os.getenv('UPSTASH_REDIS_REST_TOKEN')
        if not url or not token:
            raise ServiceError('cache_not_configured', 'Add Upstash Redis credentials to enable this service.')
        if not url.startswith('https://'):
            raise ServiceError('cache_not_configured', 'The Redis endpoint must use HTTPS.')
        try:
            response = httpx.post(url, headers={'Authorization': f'Bearer {token}'}, json=list(args), timeout=5)
            response.raise_for_status()
            payload = response.json()
            if payload.get('error'):
                raise ValueError('Redis command failed')
            return payload.get('result')
        except (httpx.HTTPError, ValueError):
            raise ServiceError('cache_unavailable', 'The shared cache is unavailable. Please try again.') from None

    @property
    def local(self):
        return local_cache_allowed() and not os.getenv('UPSTASH_REDIS_REST_URL')

    def get(self, key: str):
        if self.local:
            with self._mutex:
                expiry, value = self._data.get(key, (0, 'null'))
                return json.loads(value) if expiry > time.monotonic() else None
        value = self.command('GET', f'geoclean:{key}')
        return json.loads(value) if value is not None else None

    def put(self, key: str, value, ttl: int):
        encoded = json.dumps(value, allow_nan=False, separators=(',', ':'))
        if self.local:
            with self._mutex:
                if len(self._data) > 500:
                    self._data = {k: v for k, v in self._data.items() if v[0] > time.monotonic()}
                    if len(self._data) > 500:
                        self._data.pop(next(iter(self._data)))
                self._data[key] = (time.monotonic() + ttl, encoded)
        else:
            self.command('SET', f'geoclean:{key}', encoded, 'EX', ttl)

    def reserve(self, key: str, token: str, ttl_ms: int) -> bool:
        if self.local:
            with self._mutex:
                if self._data.get(key, (0, ''))[0] > time.monotonic():
                    return False
                self._data[key] = (time.monotonic() + ttl_ms / 1000, json.dumps(token))
                return True
        return self.command('SET', f'geoclean:{key}', json.dumps(token), 'NX', 'PX', ttl_ms) == 'OK'

    def release(self, key: str, token: str):
        if self.local:
            with self._mutex:
                if self._data.get(key, (0, ''))[1] == json.dumps(token):
                    self._data.pop(key, None)
        else:
            self.command('EVAL', "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) else return 0 end", 1, f'geoclean:{key}', json.dumps(token))

    @contextmanager
    def lease(self, key: str, ttl_ms: int = 65_000):
        token = uuid4().hex
        if not self.reserve(key, token, ttl_ms):
            raise ServiceError('busy', 'Another scan is running. Please try again shortly.', 429, 3)
        try:
            yield
        finally:
            try:
                self.release(key, token)
            except ServiceError:
                pass  # Expiring lease still prevents a permanent lock.

cache = Cache()
