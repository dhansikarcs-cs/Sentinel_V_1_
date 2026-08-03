from app.repositories.booking_repository import BookingRepository
from app.repositories.followup_repository import FollowupRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.patient_repository import PatientRepository

__all__ = [
    "PatientRepository",
    "JournalRepository",
    "BookingRepository",
    "FollowupRepository",
]
