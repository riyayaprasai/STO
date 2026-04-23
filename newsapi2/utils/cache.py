"""
Simple in-memory TTL cache.

Keys are built from a namespace + a stable JSON hash of the query params,
so callers never have to construct cache keys manually.
"""
import hashlib
import json
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    # ── key helpers ──────────────────────────────────────────────────────────

    def make_key(self, namespace: str, **params) -> str:
        raw = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"{namespace}:{digest}"

    # ── cache operations ─────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() < expires_at:
            return value
        del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


cache = TTLCache()
