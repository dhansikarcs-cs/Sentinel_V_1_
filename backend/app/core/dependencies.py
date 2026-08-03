import hashlib
import hmac as hmac_mod
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.token_blacklist import token_blacklist
from app.models.ring_device import RingDevice
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    jti = payload.get("jti", "")
    if token_blacklist.is_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    def _check(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _check


class RingIdentity:
    """Resolved identity for a /ring request: a patient user plus an optional device."""

    def __init__(self, user: User, device: RingDevice | None = None):
        self.user = user
        self.device = device


def _hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_ring_identity(
    request: Request,
    db: Session = Depends(get_db),
) -> RingIdentity:
    """Authenticate a sensor push.

    Primary path: hardware authenticates with `X-Device-Serial` + `X-Device-Token`
    headers (the device token issued by POST /ring/pair). The raw token is never
    stored — only its SHA-256 hash — and tokens are validated with a constant-time
    compare.

    Fallback path: a patient JWT (existing clients, simulated pushes from the portal).
    """
    serial = request.headers.get("X-Device-Serial") or ""
    token = request.headers.get("X-Device-Token") or ""

    if serial and token:
        device = db.query(RingDevice).filter(RingDevice.serial == serial, RingDevice.status == "paired").first()
        if not device:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Unknown device serial")
        digest = _hash_device_token(token)
        if not hmac_mod.compare_digest(digest, device.device_token_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")
        user = db.query(User).filter(User.username == device.patient_username).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Device owner not found")
        device.last_seen_at = datetime.now(UTC).isoformat()
        db.commit()
        return RingIdentity(user=user, device=device)

    user = get_current_user(request=request, credentials=None, db=db)
    return RingIdentity(user=user, device=None)
