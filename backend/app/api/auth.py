import logging
import time as _time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.config import settings
from app.core.database import get_db
from app.core.device_tracker import parse_user_agent
from app.core.location import user_timezone
from app.core.login_rate_limiter import LoginRateLimiter, login_rate_limiter
from app.core.password_validator import PasswordPolicy
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    initialize_encryption,
    is_encryption_ready,
    password_needs_rehash,
    verify_password,
)
from app.core.token_blacklist import token_blacklist
from app.events import get_event_bus
from app.models.user import User
from app.repositories import PatientRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UnlockRequest
from app.services.audit import log_audit

logger = logging.getLogger("sentinel.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

PROFESSIONAL_CODES = {
    "PSY-0001": "SENTINEL-01",
    "PSY-0002": "SENTINEL-02",
    "PSY-0003": "SENTINEL-03",
    "PSY-0004": "SENTINEL-04",
    "PSY-0005": "SENTINEL-05",
}

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

unlock_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60, lockout_seconds=300)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)
    client_ip = request.client.host if request.client else "unknown"

    is_locked, lockout_remaining = login_rate_limiter.is_locked(req.username)
    if is_locked:
        log_audit(
            "login_rate_limited",
            user=req.username,
            severity="WARNING",
            status="failure",
            details=f"Rate limited from {client_ip}, {lockout_remaining}s remaining",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {lockout_remaining} seconds.",
            headers={"Retry-After": str(lockout_remaining)},
        )

    repo = PatientRepository(db)
    user = repo.get_by_username(req.username)
    if not user:
        login_rate_limiter.record_attempt(req.username, success=False)
        log_audit(
            "login_failed",
            user=req.username,
            severity="WARNING",
            status="failure",
            details=f"User not found from {client_ip}",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.locked_until:
        try:
            lockout_end = datetime.fromisoformat(user.locked_until)
            if datetime.now(UTC) < lockout_end:
                remaining = int((lockout_end - datetime.now(UTC)).total_seconds() / 60)
                log_audit(
                    "login_locked",
                    user=req.username,
                    severity="WARNING",
                    status="failure",
                    details=f"Account locked, retry in {remaining}m",
                    device=device_info.device,
                    browser=device_info.browser,
                    db=db,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account locked. Try again in {remaining} minutes.",
                    headers={"Retry-After": str(max(1, remaining * 60))},
                )
        except ValueError:
            pass

    if not verify_password(req.password, user.password_hash or ""):
        login_rate_limiter.record_attempt(req.username, success=False)
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = (datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            log_audit(
                "account_locked",
                user=req.username,
                severity="WARNING",
                status="failure",
                details=f"Locked after {MAX_FAILED_ATTEMPTS} failed attempts from {client_ip}",
                device=device_info.device,
                browser=device_info.browser,
                db=db,
            )
        else:
            log_audit(
                "login",
                user=req.username,
                severity="WARNING",
                status="failure",
                details=f"Attempt {user.failed_attempts}/{MAX_FAILED_ATTEMPTS} from {client_ip}",
                device=device_info.device,
                browser=device_info.browser,
                db=db,
            )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    login_rate_limiter.record_attempt(req.username, success=True)
    user.failed_attempts = 0
    user.locked_until = ""
    if password_needs_rehash(user.password_hash or ""):
        user.password_hash = hash_password(req.password)
        logger.info("rehashed password for %s with Argon2id", req.username)
    db.commit()

    get_event_bus().emit("auth:login_success", username=user.username, role=user.role)
    access_token = create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "user_id": user.username,
            "name": user.name,
        }
    )
    refresh_token = create_refresh_token(user.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=28800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=86400 * 30,
        path="/",
    )

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    log_audit(
        "login_success",
        user=user.username,
        severity="INFO",
        status="success",
        details=f"Login from {device_info.device} / {device_info.browser}",
        device=device_info.device,
        browser=device_info.browser,
        db=db,
    )
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

    if user.locked_until:
        try:
            lockout_end = datetime.fromisoformat(user.locked_until)
            if datetime.now(UTC) < lockout_end:
                remaining = int((lockout_end - datetime.now(UTC)).total_seconds() / 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account locked. Try again in {remaining} minutes.",
                    headers={"Retry-After": str(max(1, remaining * 60))},
                )
        except ValueError:
            pass

    # Rotate: revoke the presented refresh token and issue a fresh pair.
    token_blacklist.revoke(jti, float(payload.get("exp", _time.time())))

    new_access = create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "user_id": user.username,
            "name": user.name,
        }
    )
    new_refresh = create_refresh_token(user.username)

    role_label = "Patient" if user.role == "patient" else "Psychologist"
    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=28800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=86400 * 30,
        path="/",
    )
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, role=role_label, name=user.name)


@router.post("/register")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    PasswordPolicy.validate_strict(req.password)
    ua = request.headers.get("user-agent", "")
    device_info = parse_user_agent(ua)

    repo = PatientRepository(db)
    existing = repo.get_by_username(req.username)
    if existing:
        log_audit(
            "registration_failed",
            user=req.username,
            severity="WARNING",
            status="failure",
            details="Username taken",
            device=device_info.device,
            browser=device_info.browser,
            db=db,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username taken")
    import os as _os

    if req.role == "psychologist":
        clinic_code = PROFESSIONAL_CODES.get(req.professional_code.strip().upper())
        if not clinic_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid professional code. Check the code you were issued.",
            )
        existing = db.query(User).filter(User.professional_code == req.professional_code.strip().upper()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This professional code is already registered to another psychologist.",
            )
        occupation = (req.occupation or "").strip()
        professional_code = req.professional_code.strip().upper()
        assigned_psych = ""
    else:
        occupation = req.occupation or ""
        professional_code = ""
        clinic_code = req.clinic_code
        assigned_psych = req.assigned_psych or ""
        if assigned_psych:
            target = repo.get_by_username(assigned_psych)
            if target is None or target.role != "psychologist":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid psychologist selection.",
                )
            if clinic_code and target.clinic_code != clinic_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The selected psychologist does not belong to your chosen clinic.",
                )

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        role=req.role,
        dob=req.dob,
        country=req.country.strip(),
        timezone=user_timezone(req.country, req.timezone),
        occupation=occupation,
        clinic_code=clinic_code,
        professional_code=professional_code,
        assigned_psych=assigned_psych,
        onboarding_step=0,
        encryption_salt=_os.urandom(16).hex(),
        created_at=datetime.now(UTC).isoformat(),
    )
    repo.add(user)
    get_event_bus().emit("auth:registered", username=req.username, role=req.role, clinic=req.clinic_code)
    log_audit(
        "registration_success",
        user=req.username,
        severity="INFO",
        status="success",
        device=device_info.device,
        browser=device_info.browser,
        db=db,
    )
    return ok(message="Registered")


@router.post("/unlock")
def unlock(req: UnlockRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    is_locked, remaining = unlock_rate_limiter.is_locked(client_ip)
    if is_locked:
        log_audit(
            "encryption_unlock_rate_limited",
            severity="WARNING",
            status="failure",
            details=f"Too many unlock attempts from {client_ip}",
            db=None,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many unlock attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )
    if is_encryption_ready():
        return ok(data={"ready": True})
    try:
        initialize_encryption(req.passphrase)
        get_event_bus().emit("encryption:unlocked")
        unlock_rate_limiter.record_attempt(client_ip, success=True)
        return ok(data={"ready": True})
    except Exception as e:
        unlock_rate_limiter.record_attempt(client_ip, success=False)
        log_audit("encryption_unlock_failed", severity="ERROR", status="failure", details=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unlock failed") from None


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    from app.core.security import decode_access_token as _decode
    from app.core.security import decode_refresh_token as _decode_refresh

    payload = _decode(token)
    if payload and payload.get("jti"):
        token_blacklist.revoke(payload["jti"], float(payload.get("exp", _time.time())))

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        r_payload = _decode_refresh(refresh_token)
        if r_payload and r_payload.get("jti"):
            token_blacklist.revoke(r_payload["jti"], float(r_payload.get("exp", _time.time())))

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return ok(message="Logged out")


@router.get("/encryption-status")
def encryption_status():
    return ok(data={"ready": is_encryption_ready()})
