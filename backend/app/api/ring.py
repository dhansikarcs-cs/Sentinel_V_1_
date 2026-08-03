import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import RingIdentity, get_current_user, get_ring_identity
from app.core.input_validator import validate_sensor_data
from app.models.ring import RingSensorLog
from app.models.ring_device import RingDevice
from app.models.user import User
from app.schemas.ring import (
    RingDeviceCreate,
    RingDeviceResponse,
    SensorDataCreate,
    SensorDataResponse,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/ring", tags=["ring"])


def _hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/pair", response_model=RingDeviceResponse)
def pair_ring_device(data: RingDeviceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(RingDevice).filter(RingDevice.serial == data.serial).first()
    now = datetime.now(UTC).isoformat()
    token = secrets.token_urlsafe(32)
    if existing:
        if existing.status == "paired":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial already paired")
        existing.patient_username = user.username
        existing.device_token_hash = _hash_device_token(token)
        existing.vendor = data.vendor
        existing.status = "paired"
        existing.last_seen_at = ""
        db.commit()
        db.refresh(existing)
        log_audit(
            "ring_device_repair",
            user=user.username,
            role=user.role,
            severity="INFO",
            status="success",
            resource=data.serial,
            db=db,
        )
        return RingDeviceResponse(
            serial=existing.serial,
            patient_username=existing.patient_username,
            vendor=existing.vendor,
            status=existing.status,
            last_seen_at=existing.last_seen_at,
            created_at=existing.created_at,
            token=token,
        )
    device = RingDevice(
        serial=data.serial,
        patient_username=user.username,
        device_token_hash=_hash_device_token(token),
        vendor=data.vendor,
        status="paired",
        created_at=now,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    log_audit(
        "ring_device_paired",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=data.serial,
        db=db,
    )
    return RingDeviceResponse(
        serial=device.serial,
        patient_username=device.patient_username,
        vendor=device.vendor,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        token=token,
    )


@router.post("/unpair")
def unpair_ring_device(serial: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(RingDevice).filter(RingDevice.serial == serial).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if device.patient_username != user.username and user.role != "psychologist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your device")
    device.status = "revoked"
    device.device_token_hash = ""
    db.commit()
    log_audit(
        "ring_device_unpaired",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=serial,
        db=db,
    )
    return {"success": True, "message": f"Device {serial} revoked"}


@router.get("/devices", response_model=list[RingDeviceResponse])
def list_ring_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(RingDevice).filter(RingDevice.patient_username == user.username)
    if user.role == "psychologist":
        q = db.query(RingDevice)
    devices = q.order_by(RingDevice.created_at.desc()).all()
    return [
        RingDeviceResponse(
            serial=d.serial,
            patient_username=d.patient_username,
            vendor=d.vendor,
            status=d.status,
            last_seen_at=d.last_seen_at,
            created_at=d.created_at,
        )
        for d in devices
    ]


@router.post("/data", response_model=SensorDataResponse)
def push_sensor_data(
    data: SensorDataCreate, identity: RingIdentity = Depends(get_ring_identity), db: Session = Depends(get_db)
):
    user = identity.user
    validate_sensor_data(
        bpm=data.bpm or 0,
        stress=data.stress or 0,
        sleep_hours=data.sleep_hours or 0,
        spo2=data.spo2 or 0,
        hrv=data.hrv or 0,
    )
    now = datetime.now(UTC).isoformat()
    device_id = data.device_id or (identity.device.serial if identity.device else "") or f"ring_{user.username}"
    log = RingSensorLog(
        device_id=device_id,
        patient_username=user.username,
        bpm=data.bpm,
        stress=data.stress,
        sleep_hours=data.sleep_hours,
        spo2=data.spo2,
        hrv=data.hrv,
        logged_at=now,
    )
    db.add(log)
    db.flush()

    from app.models.sensor_reading import SensorReading

    sr = SensorReading(
        patient_username=user.username,
        device_id=device_id,
        heart_rate=data.bpm,
        rmssd=float(data.hrv),
        sdnn=float(data.hrv) * 0.8,
        temperature=36.5,
        logged_at=now,
    )
    db.add(sr)
    db.commit()
    db.refresh(log)
    log_audit(
        "sensor_data_pushed",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        details=f"bpm={data.bpm}, stress={data.stress}, device={device_id}",
        db=db,
    )
    return log


@router.get("/data", response_model=list[SensorDataResponse])
def get_sensor_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = (
        db.query(RingSensorLog)
        .filter(RingSensorLog.patient_username == user.username)
        .order_by(RingSensorLog.logged_at.desc())
        .limit(50)
        .all()
    )
    return data
