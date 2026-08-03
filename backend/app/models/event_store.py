from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class EventRecord(Base):
    __tablename__ = "event_store"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False, index=True)
    aggregate_type = Column(String, default="")
    aggregate_id = Column(String, default="")
    payload = Column(Text, default="")
    extra_metadata = Column(Text, default="")
    sequence = Column(Integer, default=0, index=True)
    created_at = Column(String, nullable=False)
