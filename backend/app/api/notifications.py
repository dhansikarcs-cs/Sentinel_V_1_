from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationUpdate

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse)
def create_notification(data: NotificationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = Notification(
        patient_username=data.patient_username,
        title=data.title,
        message=data.message,
        notification_type=data.notification_type,
        read=0,
        sent_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.get("", response_model=list[NotificationResponse])
def get_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .filter(Notification.patient_username == user.username)
        .order_by(Notification.sent_at.desc())
        .limit(50)
        .all()
    )


@router.get("/unread", response_model=list[NotificationResponse])
def get_unread_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Notification)
        .filter(Notification.patient_username == user.username, Notification.read == 0)
        .order_by(Notification.sent_at.desc())
        .all()
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: int, data: NotificationUpdate = NotificationUpdate(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.patient_username == user.username).first()
    if notif:
        notif.read = 1 if data.read else 0
        db.commit()
        db.refresh(notif)
    return notif


@router.put("/read-all")
def mark_all_notifications_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.patient_username == user.username, Notification.read == 0).update({"read": 1})
    db.commit()
    return {"status": "ok"}
