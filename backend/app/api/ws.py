"""WebSocket endpoints — delegates to ConnectionManager."""

from fastapi import APIRouter, WebSocket, WebSocketException, status

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.core.token_blacklist import token_blacklist
from app.models.user import User
from app.services.websocket_manager import manager

router = APIRouter()


def _verify_ws_token(ws: WebSocket) -> User | None:
    token = ws.query_params.get("token") or ws.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    if token_blacklist.is_revoked(payload.get("jti", "")):
        return None
    username = payload.get("sub")
    if not username:
        return None
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
    finally:
        session.close()
    return user


@router.websocket("/ws/psych")
async def psych_websocket(ws: WebSocket):
    user = _verify_ws_token(ws)
    if not user or user.role != "psychologist":
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
    user = _verify_ws_token(ws)
    if not user or user.role != "psychologist":
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    await manager.connect_admin(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        manager.disconnect(ws)
