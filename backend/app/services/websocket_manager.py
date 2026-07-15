"""
WebSocket manager for real-time dashboard updates.
Broadcasts crisis alerts, discrepancy flags, and queue reorder events
to connected psychologist and admin clients.
"""

import json
from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._psych_clients: Set[WebSocket] = set()
        self._admin_clients: Set[WebSocket] = set()

    async def connect_psych(self, ws: WebSocket):
        await ws.accept()
        self._psych_clients.add(ws)

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self._admin_clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self._psych_clients.discard(ws)
        self._admin_clients.discard(ws)

    async def broadcast_to_psych(self, event_type: str, payload: dict):
        msg = json.dumps({"event": event_type, "data": payload})
        stale = set()
        for ws in self._psych_clients:
            try:
                await ws.send_text(msg)
            except Exception:
                stale.add(ws)
        self._psych_clients -= stale

    async def broadcast_to_admin(self, event_type: str, payload: dict):
        msg = json.dumps({"event": event_type, "data": payload})
        stale = set()
        for ws in self._admin_clients:
            try:
                await ws.send_text(msg)
            except Exception:
                stale.add(ws)
        self._admin_clients -= stale

    async def broadcast_all(self, event_type: str, payload: dict):
        await self.broadcast_to_psych(event_type, payload)
        await self.broadcast_to_admin(event_type, payload)

    @property
    def psych_count(self) -> int:
        return len(self._psych_clients)

    @property
    def admin_count(self) -> int:
        return len(self._admin_clients)


manager = ConnectionManager()
