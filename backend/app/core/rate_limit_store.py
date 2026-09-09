import logging
import threading
import time
from collections import defaultdict

from sqlalchemy import text

from app.core.database import Base, engine
from app.models.rate_limit_counter import RateLimitCounter

logger = logging.getLogger("sentinel.rate_limit_store")


class BaseRateStore:
    """Rate-limit store interface: `allows(key, window_seconds, max_requests)`.

    Backends must be safe to call from many requests concurrently. The memory
    backend is process-local (single uvicorn worker); the DB backend shares
    state across every worker/process that uses the same DATABASE_URL.
    """

    def allows(self, key: str, window_seconds: int, max_requests: int) -> bool:
        raise NotImplementedError


class MemoryRateStore(BaseRateStore):
    """Sliding-window store kept in-process. Fast, not shared across workers."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allows(self, key: str, window_seconds: int, max_requests: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        with self._lock:
            hits = [t for t in self._requests[key] if t > window_start]
            if len(hits) >= max_requests:
                self._requests[key] = hits
                return False
            hits.append(now)
            self._requests[key] = hits
            return True

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


class DBRateStore(BaseRateStore):
    """Fixed-window store persisted in the application database.

    Uses an atomic upsert so concurrent workers cannot exceed the budget; the
    row is shared across every process connected to the same DATABASE_URL.
    Works on both SQLite (>=3.35, upsert + RETURNING) and PostgreSQL.
    """

    _PRUNE_EVERY_SECONDS = 60
    _KEEP_ROWS_SECONDS = 3600

    def __init__(self):
        self._last_prune = 0.0

    def _ensure_table(self) -> None:
        Base.metadata.create_all(bind=engine, tables=[RateLimitCounter.__table__], checkfirst=True)

    def allows(self, key: str, window_seconds: int, max_requests: int) -> bool:
        self._ensure_table()
        now = int(time.time())
        window_start = now - (now % window_seconds)
        if time.time() - self._last_prune > self._PRUNE_EVERY_SECONDS:
            self._prune(now)
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO rate_limit_counters (bucket_key, window_start, count) "
                    "VALUES (:k, :w, 1) "
                    "ON CONFLICT (bucket_key, window_start) "
                    "DO UPDATE SET count = rate_limit_counters.count + 1 "
                    "RETURNING count"
                ),
                {"k": key, "w": window_start},
            ).fetchone()
            count = row[0] if row else 1
        return count <= max_requests

    def _prune(self, now: int) -> None:
        self._last_prune = now
        try:
            cutoff = int(now) - self._KEEP_ROWS_SECONDS
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM rate_limit_counters WHERE window_start < :cutoff"),
                    {"cutoff": cutoff},
                )
        except Exception as exc:  # pruning is best-effort
            logger.warning("Rate-limit counter prune failed: %s", exc)
