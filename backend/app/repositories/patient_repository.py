from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username, User.deleted_at.is_(None)).first()

    def get_by_username_raw(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_assigned_patients(self, psych_username: str) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.assigned_psych == psych_username, User.role == "patient", User.deleted_at.is_(None))
            .all()
        )

    def get_psychologists(self, clinic: str = "") -> list[User]:
        query = self.db.query(User).filter(User.role == "psychologist", User.deleted_at.is_(None))
        if clinic:
            query = query.filter(User.clinic_code == clinic)
        return query.all()

    def get_patient_summary_data(self, username: str) -> User | None:
        return self.get_by_username(username)

    def soft_delete(self, username: str, deleted_by: str = "") -> bool:
        user = self.get_by_username(username)
        if not user or user.deleted_at:
            return False
        user.deleted_at = datetime.now(UTC).isoformat()
        user.deleted_by = deleted_by
        self.db.commit()
        return True

    def restore(self, username: str) -> bool:
        user = self.get_by_username_raw(username)
        if not user or not user.deleted_at:
            return False
        user.deleted_at = None
        user.deleted_by = None
        self.db.commit()
        return True
