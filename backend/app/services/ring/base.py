"""Sensor reading container and RingSource base contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class SensorData:
    device_id: str = ""
    bpm: int = 72
    stress: int = 35
    sleep_hours: float = 7.0
    spo2: float = 98.0
    hrv: int = 50
    mood: str = ""
    timestamp: str = ""

    @classmethod
    def from_dict(cls, data: dict, device_id: str = "") -> "SensorData":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            device_id=data.get("device_id") or device_id,
            bpm=int(data.get("bpm") or 72),
            stress=int(data.get("stress") or 35),
            sleep_hours=float(data.get("sleep_hours") or data.get("sleep") or 7.0),
            spo2=float(data.get("spo2") or 98.0),
            hrv=int(data.get("hrv") or 50),
            mood=str(data.get("mood") or ""),
            timestamp=str(data.get("timestamp") or now),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class RingSource(ABC):
    """Base contract for any ring data provider."""

    name: str = "base"

    def connect(self) -> bool:
        return True

    @abstractmethod
    def read_sensors(self) -> SensorData:
        """Return the latest sensor reading."""
        raise NotImplementedError

    def disconnect(self) -> None:
        return None
