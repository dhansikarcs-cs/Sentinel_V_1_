from datetime import UTC, datetime

from app.models.notification import Notification


def create_notification(
    db,
    *,
    patient_username: str,
    title: str,
    message: str,
    notification_type: str = "info",
    recipient_username: str | None = None,
) -> Notification:
    """Insert a notification row.

    Patient-targeted notifications set only ``patient_username``. Notifications
    addressed to a psychologist (journal submitted, follow-up evaluated) set both
    ``patient_username`` (the patient the event concerns) and ``recipient_username``.
    """
    notif = Notification(
        patient_username=patient_username,
        recipient_username=recipient_username,
        title=title,
        message=message,
        notification_type=notification_type,
        read=0,
        sent_at=datetime.now(UTC).isoformat(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
