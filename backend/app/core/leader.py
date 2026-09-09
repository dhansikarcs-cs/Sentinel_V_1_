"""Scheduler leader election.

PostgreSQL deployments may run MORE than one scheduler instance (fail-over
safety). `pg_try_advisory_lock` guarantees exactly one holder: the process that
holds the lock runs the reminder/celebration sweeps; the others retry. The lock
is freed by PostgreSQL automatically when the holder's connection drops, so a
crashed leader is taken over by a replica.

Single-process deployments (SQLite) are always the leader.
"""

import asyncio
import contextlib
import logging
import threading

from app.core.config import settings

logger = logging.getLogger("sentinel.leader")


class _LockBackend:
    def try_acquire(self) -> bool:
        raise NotImplementedError

    def healthy(self) -> bool:
        return True

    def release(self) -> None:
        raise NotImplementedError


class _SqliteLock(_LockBackend):
    """Single-process layout: there is exactly one scheduler, always the leader."""

    def try_acquire(self) -> bool:
        return True

    def healthy(self) -> bool:
        return True

    def release(self) -> None:
        return None


class _PostgresAdvisoryLock(_LockBackend):
    def __init__(self, key: int, heartbeat_seconds: int):
        self._key = key
        self._heartbeat_seconds = heartbeat_seconds
        self._lock = threading.RLock()
        self._conn = None
        self._stop_heartbeat: threading.Event | None = None

    def _connect(self):
        import psycopg2

        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        return conn

    def try_acquire(self) -> bool:
        with self._lock:
            if self._conn is not None and self.healthy():
                return True
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_try_advisory_lock(%s)", (self._key,))
                    acquired = bool(cur.fetchone()[0])
                if not acquired:
                    conn.close()
                    return False
                self._conn = conn
                self._start_heartbeat()
                return True
            except Exception as exc:
                logger.warning("advisory lock acquire failed: %s", exc)
                self._conn = None
                return False

    def healthy(self) -> bool:
        with self._lock:
            return self._conn is not None

    def release(self) -> None:
        with self._lock:
            if self._stop_heartbeat is not None:
                self._stop_heartbeat.set()
            if self._conn is not None:
                with contextlib.suppress(Exception):
                    self._conn.close()  # PostgreSQL frees the advisory lock on disconnect
                self._conn = None

    def _start_heartbeat(self) -> None:
        if self._stop_heartbeat is not None and not self._stop_heartbeat.is_set():
            return
        self._stop_heartbeat = threading.Event()
        threading.Thread(target=self._heartbeat_loop, name="sentinel-leader-heartbeat", daemon=True).start()

    def _heartbeat_loop(self) -> None:
        while not self._stop_heartbeat.is_set():
            self._stop_heartbeat.wait(self._heartbeat_seconds)
            with self._lock:
                if self._conn is None:
                    return
                try:
                    with self._conn.cursor() as cur:
                        cur.execute("SELECT 1")
                except Exception as exc:
                    logger.warning("advisory lock heartbeat failed (%s); leadership will be retried", exc)
                    with contextlib.suppress(Exception):
                        self._conn.close()
                    self._conn = None
                    return


def _make_backend() -> _LockBackend:
    url = settings.database_url
    if url.startswith("postgresql") or url.startswith("postgres://"):
        return _PostgresAdvisoryLock(settings.scheduler_lock_key, settings.scheduler_heartbeat_seconds)
    return _SqliteLock()


class SchedulerLeader:
    def __init__(self, backend: _LockBackend | None = None):
        self._backend = backend or _make_backend()

    async def ensure(self) -> bool:
        """True if this process may run the scheduler loops right now."""
        if self._backend.healthy():
            return True
        acquired = await asyncio.get_running_loop().run_in_executor(None, self._backend.try_acquire)
        if acquired:
            logger.info("Scheduler leadership acquired")
        return acquired

    def release(self) -> None:
        self._backend.release()


leader = SchedulerLeader()
