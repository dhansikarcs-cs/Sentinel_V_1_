from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.sensor_reading import SensorReadingCreate, SensorReadingResponse

router = APIRouter(prefix="/sensor-readings", tags=["sensor_readings"])


@router.post("", response_model=SensorReadingResponse)
def create_sensor_reading(
    data: SensorReadingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    reading = SensorReading(
        patient_username=user.username,
        device_id=data.device_id or f"hrv_{user.username}",
        heart_rate=data.heart_rate,
        rmssd=data.rmssd,
        sdnn=data.sdnn,
        temperature=data.temperature,
        logged_at=datetime.now(UTC).isoformat(),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("", response_model=list[SensorReadingResponse])
def get_sensor_readings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(SensorReading)
        .filter(SensorReading.patient_username == user.username)
        .order_by(SensorReading.logged_at.desc())
        .limit(50)
        .all()
    )


@router.get("/patient/{username}", response_model=list[SensorReadingResponse])
def get_patient_sensor_readings(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return (
        db.query(SensorReading)
        .filter(SensorReading.patient_username == username)
        .order_by(SensorReading.logged_at.desc())
        .limit(50)
        .all()
    )
