import hashlib
import logging
import threading
import time

logger = logging.getLogger("sentinel.idempotency")


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._store: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v["ts"] > self.ttl]
        for k in expired:
            del self._store[k]

    def _make_key(self, idempotency_key: str) -> str:
        return hashlib.sha256(idempotency_key.encode()).hexdigest()

    def check(self, idempotency_key: str) -> dict | None:
        key = self._make_key(idempotency_key)
        with self._lock:
            self._cleanup()
            entry = self._store.get(key)
            if entry:
                return entry.get("result")
        return None

    def store(self, idempotency_key: str, result: dict):
        key = self._make_key(idempotency_key)
        with self._lock:
            self._store[key] = {"result": result, "ts": time.time()}

    def invalidate(self, idempotency_key: str):
        key = self._make_key(idempotency_key)
        with self._lock:
            self._store.pop(key, None)


idempotency_store = IdempotencyStore(ttl_seconds=3600)
