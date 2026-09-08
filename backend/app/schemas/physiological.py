"""Pydantic schemas for device-agnostic physiological ingestion.

The payload is intentionally loose: vendor payloads vary in structure and use
the same token names with different types (e.g. Oura's `heart_rate` is a dict,
Samsung's is a dict, generic/simulated is an int). The vendor adapter performs
all field mapping, so this schema only types the two identity fields and
passes everything else through.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class PhysiologicalPayload(BaseModel):
    """Raw vendor payload — free-form, normalized server-side by the adapter."""

    model_config = ConfigDict(extra="allow")

    vendor: str = "generic"  # oura | samsung | ring | simulated | generic
    device_id: str = ""

    # Capture any additional vendor-specific fields loosely
    def extra_payload(self) -> dict[str, Any]:
        data = self.model_dump(exclude_unset=True)
        data.pop("vendor", None)
        data.pop("device_id", None)
        return data


class NormalizedSignalResponse(BaseModel):
    id: int
    patient_username: str
    device_id: str
    vendor: str
    heart_rate: int
    hrv_rmssd: float
    stress: int
    sleep_hours: float
    spo2: float
    temperature: float
    respiratory_rate: int
    quality: str
    confidence: float
    logged_at: str

    class Config:
        from_attributes = True
