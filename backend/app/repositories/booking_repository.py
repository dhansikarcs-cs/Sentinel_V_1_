from sqlalchemy.orm import Session

from app.models.booking import Booking, PsychAvailability
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    def __init__(self, db: Session):
        super().__init__(Booking, db)

    def get_by_id(self, booking_id: int) -> Booking | None:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_for_patient(self, username: str) -> list[Booking]:
        return self.db.query(Booking).filter(Booking.patient_username == username).order_by(Booking.date.desc()).all()

    def get_for_psychologist(self, username: str) -> list[Booking]:
        return (
            self.db.query(Booking).filter(Booking.psychologist_username == username).order_by(Booking.date.desc()).all()
        )


class AvailabilityRepository(BaseRepository[PsychAvailability]):
    def __init__(self, db: Session):
        super().__init__(PsychAvailability, db)

    def get_by_psych_and_date(self, psych_username: str, date: str) -> PsychAvailability | None:
        return (
            self.db.query(PsychAvailability)
            .filter(
                PsychAvailability.psychologist_username == psych_username,
                PsychAvailability.date == date,
            )
            .first()
        )

    def get_for_psychologist(self, psych_username: str) -> list[PsychAvailability]:
        return (
            self.db.query(PsychAvailability)
            .filter(PsychAvailability.psychologist_username == psych_username)
            .order_by(PsychAvailability.date)
            .all()
        )

    def get_by_slot_id(self, slot_id: int, psych_username: str) -> PsychAvailability | None:
        return (
            self.db.query(PsychAvailability)
            .filter(
                PsychAvailability.id == slot_id,
                PsychAvailability.psychologist_username == psych_username,
            )
            .first()
        )

    def get_by_date(self, date: str, psych_username: str) -> PsychAvailability | None:
        return (
            self.db.query(PsychAvailability)
            .filter(
                PsychAvailability.psychologist_username == psych_username,
                PsychAvailability.date == date,
            )
            .first()
        )
