"""Device-agnostic physiological normalization service.

The purpose of this layer is to accept vendor-specific payloads and converge
them onto the common PhysiologicalSignal schema, so that downstream clinical
intelligence (risk engine, longitudinal analysis, four-model experiment) does
not depend on any single hardware vendor.

Design principle (from the audit):
    raw data != interpreted clinical signal.

This layer ONLY normalizes + validates. It does NOT interpret (no "HRV
high => anxious" claims).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.physiological_signal import PhysiologicalSignal


@dataclass
class NormalizedReading:
    """Canonical normalized reading produced by an adapter."""

    heart_rate: int = 0
    hrv_rmssd: float = 0.0
    stress: int = 0
    sleep_hours: float = 0.0
    spo2: float = 0.0
    temperature: float = 0.0
    respiratory_rate: int = 0
    quality: str = "unknown"
    confidence: float = 0.0
    raw_json: str = ""
    logged_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _i(v) -> int:
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ── Vendor adapters ──────────────────────────────────────────────────────────


def adapt_simulated(payload: dict) -> NormalizedReading:
    """Simulated/ring-native payload (bpm, stress, sleep_hours, spo2, hrv)."""
    return NormalizedReading(
        heart_rate=_i(payload.get("bpm", payload.get("heart_rate", 0))),
        hrv_rmssd=_f(payload.get("hrv", payload.get("hrv_rmssd", 0))),
        stress=_i(payload.get("stress", 0)),
        sleep_hours=_f(payload.get("sleep_hours", 0)),
        spo2=_f(payload.get("spo2", 0)),
        temperature=_f(payload.get("temperature", 0)),
        respiratory_rate=_i(payload.get("respiratory_rate", 0)),
        quality=str(payload.get("quality", "simulated")),
        confidence=_f(payload.get("confidence", 0.0)),
        raw_json=payload.get("raw_json", ""),
        logged_at=str(payload.get("logged_at", datetime.now(UTC).isoformat())),
    )


def adapt_oura(payload: dict) -> NormalizedReading:
    """Map an Oura-style payload to the common schema.

    Oura v2 exposes heart_rate.bpm, spo2.percentage, hr.instantaneous, sleep,
    readiness/activity. This is a best-effort mapping of the common fields.
    """
    hr = payload.get("heart_rate") or {}
    spo2 = payload.get("spo2") or {}
    sleep = payload.get("sleep") or {}

    # Approximate RMSSD from Oura's hrv if present (Oura historically reported
    # a single hrv value variously; we normalise whatever is provided).
    hrv_raw = payload.get("hrv") or {}
    hr_inst = hrv_raw.get("instantaneous") or []
    hrv_value = 0.0
    if isinstance(hr_inst, list) and hr_inst:
        hrv_value = _f(hr_inst[0])
    if not hrv_value:
        hrv_value = _f(payload.get("hrv_rmssd", 0))

    return NormalizedReading(
        heart_rate=_i(hr.get("bpm", payload.get("heart_rate_bpm", 0))),
        hrv_rmssd=hrv_value,
        stress=_i(payload.get("stress", payload.get("stress_score", 0))),
        sleep_hours=_f(sleep.get("total_sleep_duration_hours", sleep.get("duration_hours", 0))),
        spo2=_f(spo2.get("percentage", 0)),
        temperature=_f(payload.get("temperature", payload.get("body_temperature", 0))),
        respiratory_rate=_i(payload.get("respiratory_rate", 0)),
        quality=str(payload.get("quality", "good")),
        confidence=_f(payload.get("confidence", 0.0)),
        raw_json=payload.get("raw_json", ""),
        logged_at=str(payload.get("logged_at", datetime.now(UTC).isoformat())),
    )


def adapt_samsung(payload: dict) -> NormalizedReading:
    """Map a Samsung Health-style payload to the common schema.

    Samsung Health exposes heart_rate.heartRate, sleep, stress.fontion, etc.
    Best-effort mapping of common fields.
    """
    hr = payload.get("heart_rate") or {}
    sleep = payload.get("sleep") or {}
    stress = payload.get("stress") or {}

    return NormalizedReading(
        heart_rate=_i(hr.get("heartRate", hr.get("bpm", 0))),
        hrv_rmssd=_f(payload.get("hrv_rmssd", payload.get("hrv", 0))),
        stress=_i(stress.get("level", stress.get("stress", 0))),
        sleep_hours=_f(sleep.get("sleepDurationHours", sleep.get("duration_hours", 0))),
        spo2=_f(payload.get("spo2", 0)),
        temperature=_f(payload.get("bodyTemperature", payload.get("temperature", 0))),
        respiratory_rate=_i(payload.get("respiratory_rate", 0)),
        quality=str(payload.get("quality", "good")),
        confidence=_f(payload.get("confidence", 0.0)),
        raw_json=payload.get("raw_json", ""),
        logged_at=str(payload.get("logged_at", datetime.now(UTC).isoformat())),
    )


def adapt_generic(payload: dict) -> NormalizedReading:
    """Token-level mapping for any vendor that already uses similar names."""
    return NormalizedReading(
        heart_rate=_i(payload.get("heart_rate", payload.get("bpm", 0))),
        hrv_rmssd=_f(payload.get("hrv_rmssd", payload.get("rmssd", 0))),
        stress=_i(payload.get("stress", 0)),
        sleep_hours=_f(payload.get("sleep_hours", 0)),
        spo2=_f(payload.get("spo2", 0)),
        temperature=_f(payload.get("temperature", 0)),
        respiratory_rate=_i(payload.get("respiratory_rate", 0)),
        quality=str(payload.get("quality", "unknown")),
        confidence=_f(payload.get("confidence", 0.0)),
        raw_json=payload.get("raw_json", ""),
        logged_at=str(payload.get("logged_at", datetime.now(UTC).isoformat())),
    )


_ADAPTERS = {
    "simulated": adapt_simulated,
    "ring": adapt_simulated,
    "oura": adapt_oura,
    "samsung": adapt_samsung,
    "generic": adapt_generic,
}


def normalize_payload(vendor: str, payload: dict) -> NormalizedReading:
    """Route a vendor payload through the appropriate adapter.

    Unknown vendors fall back to the generic adapter rather than erroring,
    so Sentinel stays device-agnostic as new sensors appear.
    """
    adapter = _ADAPTERS.get((vendor or "generic").lower(), adapt_generic)
    return adapter(payload or {})


def to_signal_model(
    patient_username: str,
    device_id: str,
    vendor: str,
    reading: NormalizedReading,
) -> PhysiologicalSignal:
    """Convert a normalized reading into a PhysiologicalSignal ORM object."""
    return PhysiologicalSignal(
        patient_username=patient_username,
        device_id=device_id,
        vendor=(vendor or "generic").lower(),
        heart_rate=reading.heart_rate,
        hrv_rmssd=reading.hrv_rmssd,
        stress=reading.stress,
        sleep_hours=reading.sleep_hours,
        spo2=reading.spo2,
        temperature=reading.temperature,
        respiratory_rate=reading.respiratory_rate,
        quality=reading.quality,
        confidence=reading.confidence,
        raw_json=reading.raw_json,
        logged_at=reading.logged_at,
    )
