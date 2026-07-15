"""
WebSocket endpoint for real-time dashboard stream.
Connects to the ConnectionManager for broadcasting crisis/discrepancy events.
"""

from fastapi import APIRouter, WebSocket, Depends
from app.services.websocket_manager import manager
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.websocket("/ws/psych")
async def psych_websocket(ws: WebSocket):
    await manager.connect_psych(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(ws)


@router.websocket("/ws/admin")
async def admin_websocket(ws: WebSocket):
    await manager.connect_admin(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(ws)
