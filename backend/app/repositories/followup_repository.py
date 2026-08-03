from sqlalchemy.orm import Session

from app.models.followup import FollowupTask
from app.repositories.base import BaseRepository


class FollowupRepository(BaseRepository[FollowupTask]):
    def __init__(self, db: Session):
        super().__init__(FollowupTask, db)

    def get_by_id(self, followup_id: str) -> FollowupTask | None:
        return self.db.query(FollowupTask).filter(FollowupTask.id == followup_id).first()

    def get_for_patient(self, username: str) -> list[FollowupTask]:
        return (
            self.db.query(FollowupTask)
            .filter(FollowupTask.patient_username == username)
            .order_by(FollowupTask.assigned_at.desc())
            .all()
        )

    def get_for_psychologist(self, username: str) -> list[FollowupTask]:
        return (
            self.db.query(FollowupTask)
            .filter(FollowupTask.psychologist_username == username)
            .order_by(FollowupTask.assigned_at.desc())
            .all()
        )
