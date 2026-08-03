import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.event_store import EventRecord

logger = logging.getLogger("sentinel.event_store")


class EventStore:
    def __init__(self):
        self._sequence = 0

    def append(
        self,
        event_type: str,
        payload: dict,
        aggregate_type: str = "",
        aggregate_id: str = "",
        metadata: dict = None,
        db: Session = None,
    ):
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            self._sequence += 1
            record = EventRecord(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                payload=json.dumps(payload),
                extra_metadata=json.dumps(metadata or {}),
                sequence=self._sequence,
                created_at=datetime.now(UTC).isoformat(),
            )
            db.add(record)
            if own_session:
                db.commit()
            return record
        except Exception as e:
            logger.exception("Failed to append event: %s", e)
        finally:
            if own_session:
                db.close()

    def get_events(self, event_type: str = "", aggregate_id: str = "", limit: int = 100, db: Session = None):
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            q = db.query(EventRecord)
            if event_type:
                q = q.filter(EventRecord.event_type == event_type)
            if aggregate_id:
                q = q.filter(EventRecord.aggregate_id == str(aggregate_id))
            return q.order_by(EventRecord.sequence.desc()).limit(limit).all()
        finally:
            if own_session:
                db.close()

    def replay(self, from_sequence: int = 0, db: Session = None):
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            events = (
                db.query(EventRecord)
                .filter(EventRecord.sequence > from_sequence)
                .order_by(EventRecord.sequence.asc())
                .all()
            )
            for e in events:
                logger.info("Replay event %d: %s", e.sequence, e.event_type)
            return events
        finally:
            if own_session:
                db.close()


event_store = EventStore()
