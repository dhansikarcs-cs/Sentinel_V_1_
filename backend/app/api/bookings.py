from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.booking import Booking, PsychAvailability
from app.schemas.booking import BookingCreate, BookingResponse, BookingUpdate, AvailabilityCreate
from app.services.audit import log_audit

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(entry: BookingCreate, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    booking = Booking(
        patient_username=user.username,
        psychologist_username=entry.psychologist_username,
        date=entry.date,
        time=entry.time,
        session_type=entry.session_type,
        members=entry.members,
        contact=entry.contact,
        explanation=entry.explanation,
        status="Pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    log_audit("booking_created", user=user.username, role=user.role, action="create_booking", severity="INFO", status="success", resource=str(booking.id), details=f"with {entry.psychologist_username} on {entry.date}", db=db)
    return booking


@router.get("", response_model=list[BookingResponse])
def get_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "psychologist":
        bookings = db.query(Booking).filter(Booking.psychologist_username == user.username).order_by(Booking.date.desc()).all()
    else:
        bookings = db.query(Booking).filter(Booking.patient_username == user.username).order_by(Booking.date.desc()).all()
    return bookings


@router.put("/{booking_id}/status")
def update_booking_status(booking_id: int, update: BookingUpdate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return {"error": "Not found"}
    booking.status = update.status
    db.commit()
    log_audit("booking_status_updated", user=user.username, role=user.role, action="update_booking", severity="INFO", status="success", resource=str(booking_id), details=f"status={update.status}", db=db)
    return {"message": "Updated"}


@router.post("/availability")
def set_availability(entry: AvailabilityCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    existing = db.query(PsychAvailability).filter(PsychAvailability.psychologist_username == user.username, PsychAvailability.date == entry.date).first()
    if existing:
        existing.start_time = entry.start_time
        existing.end_time = entry.end_time
    else:
        avail = PsychAvailability(
            psychologist_username=user.username,
            date=entry.date,
            start_time=entry.start_time,
            end_time=entry.end_time,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(avail)
    db.commit()
    return {"message": "Availability set"}


@router.get("/availability/{psych_username}")
def get_availability(psych_username: str, db: Session = Depends(get_db)):
    slots = db.query(PsychAvailability).filter(PsychAvailability.psychologist_username == psych_username).order_by(PsychAvailability.date).all()
    return [{"date": s.date, "start": s.start_time, "end": s.end_time} for s in slots]
