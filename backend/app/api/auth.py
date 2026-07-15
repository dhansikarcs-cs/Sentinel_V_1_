from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, initialize_encryption, is_encryption_ready
from app.schemas.auth import LoginRequest, RegisterRequest, UnlockRequest, TokenResponse
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    role_label = "Patient" if user.role == "patient" else "Psychologist"
    return TokenResponse(access_token=token, role=role_label, name=user.name)


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
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
    return {"message": "Registered"}


@router.post("/unlock")
def unlock(req: UnlockRequest):
    try:
        initialize_encryption(req.passphrase)
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/encryption-status")
def encryption_status():
    return {"ready": is_encryption_ready()}
