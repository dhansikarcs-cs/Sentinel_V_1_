from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, initialize_encryption, is_encryption_ready
from app.schemas.auth import LoginRequest, RegisterRequest, UnlockRequest, TokenResponse
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        log_audit("login_failed", user=req.username, action="login", severity="WARNING", status="failure", details="User not found", db=db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.locked_until:
        try:
            lockout_end = datetime.fromisoformat(user.locked_until)
            if datetime.now(timezone.utc) < lockout_end:
                remaining = int((lockout_end - datetime.now(timezone.utc)).total_seconds() / 60)
                log_audit("login_locked", user=req.username, action="login", severity="WARNING", status="failure", details=f"Account locked, retry in {remaining}m", db=db)
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Account locked. Try again in {remaining} minutes.")
        except ValueError:
            pass

    if not verify_password(req.password, user.password_hash or ""):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            log_audit("account_locked", user=req.username, action="login", severity="WARNING", status="failure", details=f"Locked after {MAX_FAILED_ATTEMPTS} failed attempts", db=db)
        else:
            log_audit("login_failed", user=req.username, action="login", severity="WARNING", status="failure", details=f"Attempt {user.failed_attempts}/{MAX_FAILED_ATTEMPTS}", db=db)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.failed_attempts = 0
    user.locked_until = ""
    db.commit()

    log_audit("login_success", user=user.username, role=user.role, action="login", severity="INFO", status="success", db=db)
    token = create_access_token({"sub": user.username, "role": user.role})
    role_label = "Patient" if user.role == "patient" else "Psychologist"
    return TokenResponse(access_token=token, role=role_label, name=user.name)


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        log_audit("registration_failed", user=req.username, action="register", severity="WARNING", status="failure", details="Username taken", db=db)
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
    db.add(user)
    db.commit()
    log_audit("user_registered", user=req.username, role=req.role, action="register", severity="INFO", status="success", details=f"Clinic: {req.clinic_code}", db=db)
    return {"message": "Registered"}


@router.post("/unlock")
def unlock(req: UnlockRequest):
    try:
        initialize_encryption(req.passphrase)
        log_audit("encryption_unlocked", action="unlock", severity="INFO", status="success")
        return {"ready": True}
    except Exception as e:
        log_audit("encryption_unlock_failed", action="unlock", severity="ERROR", status="failure", details=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unlock failed")


@router.get("/encryption-status")
def encryption_status():
    return {"ready": is_encryption_ready()}
