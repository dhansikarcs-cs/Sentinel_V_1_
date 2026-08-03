from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_role
from app.models.user import User
from app.services.event_store_service import event_store

router = APIRouter(prefix="/events", tags=["event_store"])


@router.get("")
def list_events(
    event_type: str = "",
    aggregate_id: str = "",
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_role("psychologist")),
):
    events = event_store.get_events(event_type=event_type, aggregate_id=aggregate_id, limit=limit)
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "aggregate_type": e.aggregate_type,
            "aggregate_id": e.aggregate_id,
            "payload": e.payload,
            "metadata": e.extra_metadata,
            "sequence": e.sequence,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.get("/patient/{username}")
def get_patient_events(
    username: str,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_role("psychologist")),
):
    events = event_store.get_events(aggregate_id=username, limit=limit)
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "aggregate_id": e.aggregate_id,
            "payload": e.payload,
            "sequence": e.sequence,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.get("/replay")
def replay_events(
    from_sequence: int = Query(0, ge=0),
    user: User = Depends(require_role("psychologist")),
):
    events = event_store.replay(from_sequence=from_sequence)
    return {"events_replayed": len(events)}
