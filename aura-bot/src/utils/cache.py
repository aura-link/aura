"""Simple TTL cache para respuestas de API."""

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any):
        self._store[key] = (time.time(), value)

    def clear(self):
        self._store.clear()

    def invalidate(self, key: str):
        self._store.pop(key, None)
