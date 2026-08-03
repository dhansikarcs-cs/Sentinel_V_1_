from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import build_timeline_events, compute_change_metrics

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/{username}", response_model=TimelineResponse)
def get_timeline(
    username: str,
    days: int = Query(30, ge=1, le=90),
    user: User = Depends(require_role("psychologist")),
    db: Session = Depends(get_db),
):
    events = build_timeline_events(username, days, db)
    metrics = compute_change_metrics(username, db)

    return TimelineResponse(events=events, metrics=metrics)


@router.get("/{username}/metrics")
def get_change_metrics(
    username: str, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)
):
    return compute_change_metrics(username, db)
