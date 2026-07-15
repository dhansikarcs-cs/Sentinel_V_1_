from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.ring import RingSensorLog
from app.schemas.ring import SensorDataCreate, SensorDataResponse

router = APIRouter(prefix="/ring", tags=["ring"])


@router.post("/data", response_model=SensorDataResponse)
def push_sensor_data(data: SensorDataCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = RingSensorLog(
        device_id=data.device_id or f"ring_{user.username}",
        patient_username=user.username,
        bpm=data.bpm,
        stress=data.stress,
        sleep_hours=data.sleep_hours,
        spo2=data.spo2,
        hrv=data.hrv,
        logged_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/data", response_model=list[SensorDataResponse])
def get_sensor_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = db.query(RingSensorLog).filter(RingSensorLog.patient_username == user.username).order_by(RingSensorLog.logged_at.desc()).limit(50).all()
    return data
