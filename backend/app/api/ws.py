"""WebSocket endpoints — delegates to ConnectionManager."""

from fastapi import APIRouter, WebSocket, WebSocketException, status

from app.core.security import decode_access_token
from app.services.websocket_manager import manager

router = APIRouter()


async def _verify_ws_token(ws: WebSocket) -> str | None:
    token = ws.query_params.get("token") or ws.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        return None
    payload = decode_access_token(token)
    return payload.get("sub") if payload else None


@router.websocket("/ws/psych")
async def psych_websocket(ws: WebSocket):
    user = await _verify_ws_token(ws)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
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
    user = await _verify_ws_token(ws)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    await manager.connect_admin(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(ws)
