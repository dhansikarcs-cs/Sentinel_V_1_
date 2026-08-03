from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_refresh_token, initialize_encryption, is_encryption_ready
from app.core.token_blacklist import token_blacklist
from app.core.password_validator import PasswordPolicy
from app.core.login_rate_limiter import login_rate_limiter
from app.core.device_tracker import parse_user_agent
from app.core.api_response import ok, fail
from app.schemas.auth import LoginRequest, RegisterRequest, UnlockRequest, TokenResponse, RefreshRequest
from app.models.user import User
from app.repositories import PatientRepository
from app.events import get_event_bus
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)
    client_ip = request.client.host if request.client else "unknown"

    is_locked, lockout_remaining = login_rate_limiter.is_locked(req.username)
    if is_locked:
        log_audit("login_rate_limited", user=req.username, severity="WARNING", status="failure",
                  details=f"Rate limited from {client_ip}, {lockout_remaining}s remaining",
                  device=device_info.device, browser=device_info.browser, db=db)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {lockout_remaining} seconds.",
        )

    repo = PatientRepository(db)
    user = repo.get_by_username(req.username)
    if not user:
        login_rate_limiter.record_attempt(req.username, success=False)
        log_audit("login_failed", user=req.username, severity="WARNING", status="failure",
                  details=f"User not found from {client_ip}",
                  device=device_info.device, browser=device_info.browser, db=db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.locked_until:
        try:
            lockout_end = datetime.fromisoformat(user.locked_until)
            if datetime.now(timezone.utc) < lockout_end:
                remaining = int((lockout_end - datetime.now(timezone.utc)).total_seconds() / 60)
                log_audit("login_locked", user=req.username, severity="WARNING", status="failure",
                          details=f"Account locked, retry in {remaining}m",
                          device=device_info.device, browser=device_info.browser, db=db)
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Account locked. Try again in {remaining} minutes.")
        except ValueError:
            pass

    if not verify_password(req.password, user.password_hash or ""):
        login_rate_limiter.record_attempt(req.username, success=False)
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            log_audit("account_locked", user=req.username, severity="WARNING", status="failure",
                      details=f"Locked after {MAX_FAILED_ATTEMPTS} failed attempts from {client_ip}",
                      device=device_info.device, browser=device_info.browser, db=db)
        else:
            log_audit("login", user=req.username, severity="WARNING", status="failure",
                      details=f"Attempt {user.failed_attempts}/{MAX_FAILED_ATTEMPTS} from {client_ip}",
                      device=device_info.device, browser=device_info.browser, db=db)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    login_rate_limiter.record_attempt(req.username, success=True)
    user.failed_attempts = 0
    user.locked_until = ""
    db.commit()

    get_event_bus().emit("auth:login_success", username=user.username, role=user.role)
    access_token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "user_id": user.username,
        "name": user.name,
    })
    refresh_token = create_refresh_token(user.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=28800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30,
        path="/auth/refresh",
    )

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    log_audit("login_success", user=user.username, severity="INFO", status="success",
              details=f"Login from {device_info.device} / {device_info.browser}",
              device=device_info.device, browser=device_info.browser, db=db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=role_label, name=user.name)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    token = req.refresh_token
    payload = decode_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload.get("jti", "")
    if token_blacklist.is_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    username = payload.get("sub")
    repo = PatientRepository(db)
    user = repo.get_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token({
        "sub": user.username,
        "role": user.role,
        "user_id": user.username,
        "name": user.name,
    })

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        max_age=28800,
        path="/",
    )
    return TokenResponse(access_token=new_access, refresh_token=token, role=role_label, name=user.name)


@router.post("/register")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    PasswordPolicy.validate_strict(req.password)
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)

    repo = PatientRepository(db)
    existing = repo.get_by_username(req.username)
    if existing:
        log_audit("registration_failed", user=req.username, severity="WARNING", status="failure",
                  details="Username taken",
                  device=device_info.device, browser=device_info.browser, db=db)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username taken")
    import os as _os
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        role=req.role,
        age=req.age,
        occupation=req.occupation,
        clinic_code=req.clinic_code,
        onboarding_step=0,
        encryption_salt=_os.urandom(16).hex(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.add(user)
    get_event_bus().emit("auth:registered", username=req.username, role=req.role, clinic=req.clinic_code)
    log_audit("registration_success", user=req.username, severity="INFO", status="success",
              device=device_info.device, browser=device_info.browser, db=db)
    return ok(message="Registered")


@router.post("/unlock")
def unlock(req: UnlockRequest):
    try:
        initialize_encryption(req.passphrase)
        get_event_bus().emit("encryption:unlocked")
        return ok(data={"ready": True})
    except Exception as e:
        log_audit("encryption_unlock_failed", severity="ERROR", status="failure", details=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unlock failed")


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if token:
        from app.core.security import decode_access_token as _decode
        payload = _decode(token)
        if payload and payload.get("jti"):
            import time as _time
            token_blacklist.revoke(payload["jti"], _time.time() + (payload.get("exp", 0) - _time.time()))
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return ok(message="Logged out")


@router.get("/encryption-status")
def encryption_status():
    return ok(data={"ready": is_encryption_ready()})
