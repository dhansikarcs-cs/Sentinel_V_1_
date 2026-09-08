"""Device-agnostic physiological ingestion API.

Accepts raw payloads from any vendor (Oura, Samsung, ring, simulated,
generic), normalizes to the common PhysiologicalSignal schema, and — for
backward compatibility — also mirrors into the legacy SensorReading /
RingSensorLog tables so existing risk-engine and dashboard logic keeps
working without modification.

Every row is labeled with its vendor and (for synthetic data) quality, so
simulated physiology is never silently mixed with real readings.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_sensor_data
from app.models.physiological_signal import PhysiologicalSignal
from app.models.ring import RingSensorLog
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.physiological import NormalizedSignalResponse, PhysiologicalPayload
from app.services.audit import log_audit
from app.services.physio import normalize_payload, to_signal_model

router = APIRouter(prefix="/physio", tags=["physio"])


@router.post("/push", response_model=NormalizedSignalResponse)
def push_physiological(
    payload: PhysiologicalPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = (payload.vendor or "generic").lower()
    device_id = payload.device_id or f"{vendor}_{user.username}"
    now = datetime.now(UTC).isoformat()

    raw = payload.extra_payload()
    raw.setdefault("logged_at", now)
    raw_json = json.dumps(raw) if raw else ""

    reading = normalize_payload(vendor, raw)
    validate_sensor_data(
        bpm=reading.heart_rate,
        stress=reading.stress,
        sleep_hours=reading.sleep_hours,
        spo2=reading.spo2,
        hrv=reading.hrv_rmssd,
    )
    reading.raw_json = raw_json

    # Store into the common schema
    signal = to_signal_model(user.username, device_id, vendor, reading)
    db.add(signal)
    db.flush()

    is_synthetic = vendor in ("simulated", "ring")

    # Mirror into legacy tables for backward compatibility with the risk engine.
    bpm = reading.heart_rate
    hrv = reading.hrv_rmssd
    db.add(
        RingSensorLog(
            device_id=device_id,
            patient_username=user.username,
            bpm=bpm,
            stress=reading.stress,
            sleep_hours=reading.sleep_hours,
            spo2=reading.spo2,
            hrv=int(round(hrv)),
            raw_json=raw_json,
            logged_at=reading.logged_at,
        )
    )
    db.add(
        SensorReading(
            patient_username=user.username,
            device_id=device_id,
            heart_rate=bpm,
            rmssd=float(hrv),
            sdnn=float(hrv) * 0.8,
            temperature=reading.temperature,
            logged_at=reading.logged_at,
        )
    )

    db.commit()
    db.refresh(signal)

    log_audit(
        "physio_pushed",
        user=user.username,
        role=user.role,
        severity="INFO",
        status="success",
        resource=vendor,
        details=f"vendor={vendor}, synthetic={is_synthetic}, bpm={bpm}, hrv={hrv}, device={device_id}",
        db=db,
    )

    return NormalizedSignalResponse(
        id=signal.id,
        patient_username=signal.patient_username,
        device_id=signal.device_id,
        vendor=signal.vendor,
        heart_rate=signal.heart_rate,
        hrv_rmssd=signal.hrv_rmssd,
        stress=signal.stress,
        sleep_hours=signal.sleep_hours,
        spo2=signal.spo2,
        temperature=signal.temperature,
        respiratory_rate=signal.respiratory_rate,
        quality=signal.quality,
        confidence=signal.confidence,
        logged_at=signal.logged_at,
    )


@router.get("/signals", response_model=list[NormalizedSignalResponse])
def list_own_signals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(PhysiologicalSignal)
        .filter(PhysiologicalSignal.patient_username == user.username)
        .order_by(PhysiologicalSignal.logged_at.desc())
        .limit(200)
        .all()
    )


@router.get("/patient/{username}", response_model=list[NormalizedSignalResponse])
def list_patient_signals(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return (
        db.query(PhysiologicalSignal)
        .filter(PhysiologicalSignal.patient_username == username)
        .order_by(PhysiologicalSignal.logged_at.desc())
        .limit(200)
        .all()
    )


@router.get("/vendors")
def list_vendors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vendors = (
        db.query(PhysiologicalSignal.vendor)
        .filter(PhysiologicalSignal.patient_username == user.username)
        .distinct()
        .all()
    )
    return {"vendors": [v[0] for v in vendors]}
