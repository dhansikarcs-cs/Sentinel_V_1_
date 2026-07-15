import hashlib, json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, BigInteger
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False, index=True)
    user = Column(String, default="", index=True)
    role = Column(String, default="")
    action = Column(String, nullable=False, index=True)
    resource = Column(String, default="")
    resource_id = Column(String, default="")
    severity = Column(String, default="INFO")
    status = Column(String, default="success")
    ip = Column(String, default="")
    details = Column(Text, default="")
    prev_hash = Column(String, default="")
    curr_hash = Column(String, unique=True, nullable=False)

    def compute_hash(self) -> str:
        raw = f"{self.prev_hash}|{self.timestamp}|{self.user}|{self.action}|{self.resource}|{self.resource_id}|{self.status}|{self.details}|{self.severity}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "time": self.timestamp,
            "user": self.user,
            "role": self.role,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "severity": self.severity,
            "status": self.status,
            "ip": self.ip,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "curr_hash": self.curr_hash,
        }
