from sqlalchemy import Column, Integer, String, Index

from app.core.database import Base


class RingDevice(Base):
    __tablename__ = "ring_devices"
    __table_args__ = (
        Index("ix_ring_device_serial", "serial", unique=True),
        Index("ix_ring_device_patient", "patient_username"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String, nullable=False, default="")
    patient_username = Column(String, nullable=False, default="")
    device_token_hash = Column(String, nullable=False, default="")
    vendor = Column(String, default="simulated")
    status = Column(String, default="paired")
    last_seen_at = Column(String, default="")
    created_at = Column(String, nullable=False)
