from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.followup import FollowupTask
from app.schemas.followup import FollowupCreate, FollowupUpdate, FollowupResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/followups", tags=["followups"])


@router.post("", response_model=FollowupResponse)
def create_followup(entry: FollowupCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    task = FollowupTask(
        id=str(uuid.uuid4())[:8],
        patient_username=entry.patient_username,
        psychologist_username=user.username,
        title=entry.title,
        description=entry.description,
        status="pending",
        assigned_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_audit("followup_created", user=user.username, role=user.role, action="create_followup", severity="INFO", status="success", resource=task.id, details=f"patient={entry.patient_username}, title={entry.title}", db=db)
    return task


@router.get("", response_model=list[FollowupResponse])
def get_followups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "psychologist":
        tasks = db.query(FollowupTask).filter(FollowupTask.psychologist_username == user.username).order_by(FollowupTask.assigned_at.desc()).all()
    else:
        tasks = db.query(FollowupTask).filter(FollowupTask.patient_username == user.username).order_by(FollowupTask.assigned_at.desc()).all()
    return tasks


@router.put("/{task_id}", response_model=FollowupResponse)
def update_followup(task_id: str, update: FollowupUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(FollowupTask).filter(FollowupTask.id == task_id).first()
    if not task:
        return {"error": "Not found"}
    if update.status:
        task.status = update.status
        if update.status == "completed":
            task.completed_at = datetime.now(timezone.utc).isoformat()
    if update.grade:
        task.grade = update.grade
    db.commit()
    db.refresh(task)
    log_audit("followup_updated", user=user.username, role=user.role, action="update_followup", severity="INFO", status="success", resource=task_id, details=f"status={update.status}, grade={update.grade}", db=db)
    return task
