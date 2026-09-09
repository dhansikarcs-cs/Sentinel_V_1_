"""WS broadcast for crisis/discrepancy alerts to dashboard clients.

Single process (SQLite): broadcasts reach local clients directly.
Multi-worker (PostgreSQL): broadcasts fan out via LISTEN/NOTIFY so a client
connected to ANY API worker receives the alert. The publishing worker also
listens, so messages are not duplicated.
"""

import asyncio
import json

from fastapi import WebSocket

from app.services import ws_pubsub


class ConnectionManager:
    def __init__(self):
        self._psych_clients: set[WebSocket] = set()
        self._admin_clients: set[WebSocket] = set()
        self._listener = ws_pubsub.WsPubSubListener(self._dispatch_message)
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start_pubsub(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._listener.start()

    def stop_pubsub(self) -> None:
        self._listener.stop()
        self._loop = None

    # ── client tracking ──────────────────────────────────────────────────────

    async def connect_psych(self, ws: WebSocket):
        await ws.accept()
        self._psych_clients.add(ws)

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self._admin_clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self._psych_clients.discard(ws)
        self._admin_clients.discard(ws)

    # ── broadcast API (unchanged for callers: ai_worker, discrepancy route) ──

    async def broadcast_to_psych(self, event_type: str, payload: dict):
        await self._broadcast("psych", event_type, payload)

    async def broadcast_to_admin(self, event_type: str, payload: dict):
        await self._broadcast("admin", event_type, payload)

    async def broadcast_all(self, event_type: str, payload: dict):
        await self._broadcast("psych", event_type, payload)
        await self._broadcast("admin", event_type, payload)

    # ── internals ────────────────────────────────────────────────────────────

    async def _broadcast(self, channel: str, event_type: str, payload: dict):
        if ws_pubsub.pubsub_enabled():
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, ws_pubsub.publish, {"to": channel, "event": event_type, "payload": payload}
            )
            return
        await self._deliver_local(channel, event_type, payload)

    def _dispatch_message(self, message: dict) -> None:
        """Called from the pub/sub listener thread."""
        loop = self._loop
        if loop is None:
            return
        loop.call_soon_threadsafe(self._schedule_message, message)

    def _schedule_message(self, message: dict) -> None:
        asyncio.create_task(
            self._deliver_local(message.get("to", "psych"), message.get("event", ""), message.get("payload", {}))
        )

    async def _deliver_local(self, channel: str, event_type: str, payload: dict) -> None:
        msg = json.dumps({"event": event_type, "data": payload})
        stale = set()
        if channel in ("psych", "all"):
            for ws in self._psych_clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    stale.add(ws)
            self._psych_clients -= stale
        if channel in ("admin", "all"):
            for ws in self._admin_clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    stale.add(ws)
            self._admin_clients -= stale

    # ── metrics ──────────────────────────────────────────────────────────────

    @property
    def psych_count(self) -> int:
        return len(self._psych_clients)

    @property
    def admin_count(self) -> int:
        return len(self._admin_clients)


manager = ConnectionManager()
