"""Cross-process WebSocket fan-out via PostgreSQL LISTEN/NOTIFY (no extra infra).

Every API worker keeps one dedicated psycopg2 connection LISTENing on a
channel. `publish()` emits a JSON payload with `pg_notify` and EVERY worker
(including the publisher) receives it and delivers to its own local clients, so
a dashboard client connected to any worker sees the alert.

On SQLite a single process can broadcast locally and no listener is started.
"""

import contextlib
import json
import logging
import select
import threading
from collections.abc import Callable

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger("sentinel.ws_pubsub")

CHANNEL = "sentinel_ws"


def is_postgres() -> bool:
    url = settings.database_url
    return url.startswith("postgresql") or url.startswith("postgres://")


def pubsub_enabled() -> bool:
    if settings.ws_pubsub == "off":
        return False
    return True if settings.ws_pubsub == "pg" else is_postgres()


def publish(payload: dict) -> None:
    """Best-effort publish; failures must never break the caller."""
    if not pubsub_enabled():
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_notify(:chan, :payload)"), {"chan": CHANNEL, "payload": json.dumps(payload)})
    except Exception as exc:  # pragma: no cover — depends on a live PG
        logger.warning("pg_notify publish failed: %s", exc)


class WsPubSubListener:
    """Dedicated PG connection + thread that LISTENs on the channel."""

    def __init__(self, dispatch: Callable[[dict], None]):
        self._dispatch = dispatch
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False

    def start(self) -> None:
        if not pubsub_enabled():
            return
        self._stop.clear()
        self._active = True
        self._thread = threading.Thread(target=self._run, name="sentinel-ws-listener", daemon=True)
        self._thread.start()
        logger.info("WS pub/sub listener started on channel %s", CHANNEL)

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _connect(self):
        import psycopg2

        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"LISTEN {CHANNEL}")
        return conn

    def _run(self) -> None:
        conn = None
        while not self._stop.is_set():
            if conn is None:
                try:
                    conn = self._connect()
                except Exception as exc:
                    logger.warning("ws pub/sub listener connect failed: %s", exc)
                    self._stop.wait(2)
                    continue
            try:
                ready, _, _ = select.select([conn.fileno()], [], [], 1.0)
                if ready:
                    conn.poll()
                    for notify in conn.notifies:
                        try:
                            payload = json.loads(notify.payload)
                        except json.JSONDecodeError:
                            continue
                        self._dispatch(payload)
                    conn.notifies.clear()
            except Exception as exc:
                logger.warning("ws pub/sub listener error (%s); reconnecting", exc)
                with contextlib.suppress(Exception):
                    conn.close()
                conn = None
