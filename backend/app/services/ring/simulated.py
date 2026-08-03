"""Deterministic simulated ring for development, testing, and demos.

Seeds a per-user, per-hour random stream so behaviour is reproducible:
the same patient at the same hour always produces the same readings. This
mirrors the original Streamlit `SimulatedRing` contract.
"""

import random
from datetime import UTC, datetime

from app.services.ring.base import RingSource, SensorData

SCENARIOS = {
    "calm": {"bpm_lo": 55, "bpm_hi": 78, "stress_lo": 10, "stress_hi": 45, "hrv_lo": 55},
    "balanced": {"bpm_lo": 62, "bpm_hi": 98, "stress_lo": 35, "stress_hi": 65, "hrv_lo": 40},
    "stressed": {"bpm_lo": 85, "bpm_hi": 145, "stress_lo": 60, "stress_hi": 95, "hrv_lo": 15},
}


def _hour_seed(username: str, hour: str) -> random.Random:
    return random.Random(f"sentinel:{username}:{hour}")


class SimulatedRing(RingSource):
    name = "simulated"

    def __init__(self, username: str = "", device_id: str = "", scenario: str = "balanced"):
        self.username = username
        self.device_id = device_id or f"ring_{username}" if username else "ring_sim"
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'; choose from {list(SCENARIOS)}")
        self.scenario = scenario
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def read_sensors(self) -> SensorData:
        if not self._connected:
            self.connect()
        cfg = SCENARIOS[self.scenario]
        now = datetime.now(UTC)
        rng = _hour_seed(self.username or self.device_id, now.strftime("%Y-%m-%d-%H"))

        bpm = rng.randint(cfg["bpm_lo"], cfg["bpm_hi"])
        stress = rng.randint(cfg["stress_lo"], cfg["stress_hi"])
        sleep_hours = round(rng.uniform(4.5, 9.0), 1)
        spo2 = round(rng.uniform(94.0, 99.5), 1)
        hrv = rng.randint(cfg["hrv_lo"], 90)

        # Sleep only makes sense at night; daytime readings report 0.
        if not (now.hour >= 22 or now.hour <= 6):
            sleep_hours = 0.0

        moods = ["calm", "neutral", "focused", "anxious"]
        mood = "stressed" if stress >= 80 else rng.choice(moods)

        return SensorData(
            device_id=self.device_id,
            bpm=bpm,
            stress=stress,
            sleep_hours=sleep_hours,
            spo2=spo2,
            hrv=hrv,
            mood=mood,
            timestamp=now.isoformat(),
        )
