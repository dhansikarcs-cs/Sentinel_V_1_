from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/journals")
def search_journals(
    q: str = Query(..., min_length=1),
    patient_username: str = "",
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "patient":
        patient_username = user.username
    results = search_service.search_journals(db, q, patient_username=patient_username, limit=limit)
    return {"query": q, "results": results, "count": len(results)}
