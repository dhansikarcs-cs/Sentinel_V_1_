import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.api_response import ok
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.input_validator import validate_file_upload
from app.events import get_event_bus
from app.models.followup import FollowupTask
from app.models.user import User
from app.repositories import FollowupRepository
from app.schemas.followup import FollowupCreate, FollowupResponse, FollowupUpdate

UPLOAD_DIR = "data/followup_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
PROOF_DIR = "data/followup_proofs"
os.makedirs(PROOF_DIR, exist_ok=True)

router = APIRouter(prefix="/followups", tags=["followups"])


@router.post("", response_model=FollowupResponse)
def create_followup(
    entry: FollowupCreate, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = FollowupTask(
        id=str(uuid.uuid4())[:8],
        patient_username=entry.patient_username,
        psychologist_username=user.username,
        title=entry.title,
        description=entry.description,
        status="pending",
        assigned_at=datetime.now(UTC).isoformat(),
    )
    repo.add(task)
    get_event_bus().emit(
        "followup:created",
        task_id=task.id,
        psych=user.username,
        patient_username=entry.patient_username,
        title=entry.title,
    )
    return task


@router.get("", response_model=list[FollowupResponse])
def get_followups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = FollowupRepository(db)
    if user.role == "psychologist":
        return repo.get_for_psychologist(user.username)
    return repo.get_for_patient(user.username)


@router.put("/{task_id}", response_model=FollowupResponse)
def update_followup(
    task_id: str, update: FollowupUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        return {"error": "Not found"}
    if update.status:
        task.status = update.status
        if update.status == "completed":
            task.completed_at = datetime.now(UTC).isoformat()
    if update.grade:
        task.grade = update.grade
    db.commit()
    db.refresh(task)
    get_event_bus().emit(
        "followup:updated",
        task_id=task_id,
        patient_username=task.patient_username,
        user=user.username,
        status=update.status,
        grade=update.grade,
    )
    return task


@router.post("/{task_id}/upload")
async def upload_followup_file(
    task_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Followup not found")
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "file")[1]
    fname = f"{task_id}{ext}"
    dest = os.path.join(UPLOAD_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    task.file_path = dest
    db.commit()
    db.refresh(task)
    return ok(data={"file_path": dest, "task_id": task_id})


@router.post("/{task_id}/upload-proof")
async def upload_followup_proof(
    task_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Followup not found")
    content = await validate_file_upload(file)
    ext = os.path.splitext(file.filename or "file")[1]
    fname = f"proof_{task_id}{ext}"
    dest = os.path.join(PROOF_DIR, fname)
    with open(dest, "wb") as f:
        f.write(content)
    task.file_path = dest
    task.status = "completed"
    task.completed_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(task)
    return ok(data={"file_path": dest, "task_id": task_id})


@router.get("/{task_id}/download")
def download_followup_file(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    repo = FollowupRepository(db)
    task = repo.get_by_id(task_id)
    if not task or not task.file_path:
        return {"error": "Not found"}
    if not os.path.exists(task.file_path):
        return {"error": "File not found on disk"}
    return FileResponse(task.file_path, filename=os.path.basename(task.file_path))
