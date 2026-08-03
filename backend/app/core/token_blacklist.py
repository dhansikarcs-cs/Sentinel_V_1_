import time
import threading
from typing import Optional


class TokenBlacklist:
    """In-memory token blacklist for revoked JWTs. Replace with Redis in production."""

    def __init__(self):
        self._store: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: float = 0):
        with self._lock:
            self._store[jti] = expires_at or (time.time() + 86400)

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            expires = self._store.get(jti)
            if expires is None:
                return False
            if time.time() > expires:
                del self._store[jti]
                return False
            return True

    def _cleanup(self):
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now > v]
            for k in expired:
                del self._store[k]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)


token_blacklist = TokenBlacklist()
