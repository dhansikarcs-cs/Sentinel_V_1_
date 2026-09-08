"""Device-agnostic normalized physiological signal storage.

This is the common schema that all vendor adapters (Oura, Samsung, ring,
simulated) converge on before the intelligence layer reads them. It keeps
raw data separated from interpreted clinical signals, and preserves
provenance (source, quality, confidence) for the four-model experiment.

Numeric columns (heart_rate, hrv, ...) stay plaintext BY DESIGN so the risk
engine and longitudinal analysis can query them. raw_json (the original
vendor payload) is encrypted.
"""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String

from app.core.database import Base
from app.core.encrypted_fields import EncryptedText


class PhysiologicalSignal(Base):
    """One normalized physiological measurement from any device/vendor."""

    __tablename__ = "physiological_signals"
    __table_args__ = (
        Index("ix_physio_patient_time", "patient_username", "logged_at"),
        Index("ix_physio_device", "device_id"),
        Index("ix_physio_vendor", "vendor"),
        Index("ix_physio_logged_at", "logged_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_username = Column(String, ForeignKey("patient_profiles.username"), nullable=False)
    device_id = Column(String, default="")
    vendor = Column(String, default="generic")  # oura | samsung | ring | simulated | generic

    # Normalized vitals (kept numeric/queryable by design)
    heart_rate = Column(Integer, default=0)
    hrv_rmssd = Column(Float, default=0.0)  # heart rate variability (ms)
    stress = Column(Integer, default=0)  # 0-100
    sleep_hours = Column(Float, default=0.0)
    spo2 = Column(Float, default=0.0)  # 0-100 %
    temperature = Column(Float, default=0.0)  # deg C
    respiratory_rate = Column(Integer, default=0)

    # Provenance / quality (for the four-model experiment)
    quality = Column(String, default="unknown")  # good | fair | poor | unknown
    confidence = Column(Float, default=0.0)  # 0-1

    # Raw vendor payload (encrypted) — provenance only, not interpreted
    raw_json = Column(EncryptedText, default="")

    logged_at = Column(String, nullable=False)
