from sqlalchemy import Column, Integer, String

from app.core.database import Base


class RateLimitCounter(Base):
    __tablename__ = "rate_limit_counters"

    bucket_key = Column(String, primary_key=True)
    window_start = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False, default=1)
