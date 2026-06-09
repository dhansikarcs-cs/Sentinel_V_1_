import random
import struct
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable


# ── Data Models ──────────────────────────────────────────

@dataclass
class IMUData:
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    mag_x: float = 0.0
    mag_y: float = 0.0
    mag_z: float = 0.0


@dataclass
class PPGData:
    bpm: int = 72
    spo2: float = 97.0
    hr_signal: list = field(default_factory=list)


@dataclass
class SensorData:
    timestamp: str = ""
    bpm: int = 72
    stress: int = 35
    sleep: float = 7.0
    spo2: float = 97.0
    mood: str = "neutral"
    imu: IMUData = field(default_factory=IMUData)
    temperature: float = 36.5

    def to_dict(self):
        d = asdict(self)
        d["imu"] = asdict(self.imu)
        return d


# ── BLE Protocol Specification ───────────────────────────
# Matches the GATT service expected from Jointport firmware
#
# Service UUID:  0000SENT-0000-1000-8000-00805F9B34FB
# Characteristics:
#   BATT        0x2A19  — battery level (%)
#   HR          0x2A37  — heart rate measurement (notify)
#   PPG_WAVE    0000PPG1-0000-1000-8000-00805F9B34FB — raw PPG waveform (notify)
#   IMU_DATA    0000IMU1-0000-1000-8000-00805F9B34FB — 9-axis IMU (notify)
#   TEMP        0x2A6E  — temperature
#   CMD         0000CMD1-0000-1000-8000-00805F9B34FB — write commands to ring
#
# Binary protocol for HR characteristic (0x2A37):
#   Byte 0: flags (bit0=0 → BPM in uint8, bit0=1 → BPM in uint16)
#   Byte 1: BPM (uint8)
#   Byte 2+: RR interval (optional, uint16)
#
# Binary protocol for PPG_WAVE characteristic:
#   Byte 0-1: raw PPG sample (int16 little-endian)
#   Byte 2-3: LED index (0=green, 1=red, 2=IR)
#
# Binary protocol for IMU_DATA characteristic:
#   Byte 0-1: accel X (int16, mg)
#   Byte 2-3: accel Y
#   Byte 4-5: accel Z
#   Byte 6-7: gyro X (int16, mdps)
#   Byte 8-9: gyro Y
#   Byte 10-11: gyro Z

BLE_SERVICE_UUID = "0000SENT-0000-1000-8000-00805F9B34FB"
BLE_HR_UUID = "00002A37-0000-1000-8000-00805F9B34FB"
BLE_PPG_UUID = "0000PPG1-0000-1000-8000-00805F9B34FB"
BLE_IMU_UUID = "0000IMU1-0000-1000-8000-00805F9B34FB"
BLE_TEMP_UUID = "00002A6E-0000-1000-8000-00805F9B34FB"
BLE_CMD_UUID = "0000CMD1-0000-1000-8000-00805F9B34FB"


def encode_hr_notification(bpm: int) -> bytes:
    return struct.pack("<BB", 0, bpm)


def encode_ppg_sample(sample: int, led_idx: int = 0) -> bytes:
    return struct.pack("<hh", sample, led_idx)


def encode_imu_data(accel_mg: tuple, gyro_mdps: tuple) -> bytes:
    ax, ay, az = accel_mg
    gx, gy, gz = gyro_mdps
    return struct.pack("<hhhhhh", ax, ay, az, gx, gy, gz)


def decode_hr_notification(data: bytes) -> int:
    flags = data[0]
    if flags & 0x01:
        return struct.unpack_from("<H", data, 1)[0]
    return data[1]


def decode_imu_data(data: bytes) -> tuple:
    vals = struct.unpack("<hhhhhh", data[:12])
    return {"accel_mg": vals[:3], "gyro_mdps": vals[3:]}


def decode_cmd_write(data: bytes) -> str:
    return data.decode("ascii", errors="replace").strip()


# ── Ring Data Source Interface ───────────────────────────

class RingDataSource:
    def connect(self, device_id: str) -> bool: ...
    def disconnect(self): ...
    def read_sensors(self) -> SensorData: ...
    def start_streaming(self, callback: Callable[[SensorData], None]): ...
    def stop_streaming(self): ...


# ── Simulated Ring (default demo) ────────────────────────

class SimulatedRing(RingDataSource):
    def __init__(self):
        self.device_id = ""
        self.streaming = False

    def connect(self, device_id: str) -> bool:
        self.device_id = device_id
        return True

    def disconnect(self):
        self.streaming = False

    def read_sensors(self, intensity: float = 1.0) -> SensorData:
        seed = hash(self.device_id + datetime.now().strftime("%Y%m%d%H")) % (2**31)
        rng = random.Random(seed)

        base_bpm = 72 + rng.randint(-8, 8)
        bpm = int(base_bpm * (0.9 + 0.2 * intensity))
        stress = min(100, max(5, int(rng.gauss(35, 15) * intensity)))
        sleep = round(max(3, min(10, rng.gauss(7, 1.2) - (intensity - 1) * 0.5)), 1)
        spo2 = round(min(100, max(90, rng.gauss(97, 1.0) - (intensity - 1) * 0.3)), 1)

        mood_opts = ["calm", "neutral", "anxious", "sad", "happy", "irritable", "fatigued"]
        weights = [0.2, 0.3, 0.15, 0.1, 0.1, 0.05, 0.1]
        if intensity > 1.3:
            weights = [0.05, 0.15, 0.25, 0.2, 0.02, 0.2, 0.13]
        mood = rng.choices(mood_opts, weights=weights, k=1)[0]

        imu = IMUData(
            accel_x=rng.gauss(0, 2),
            accel_y=rng.gauss(0, 2),
            accel_z=9.81 + rng.gauss(0, 0.5),
            gyro_x=rng.gauss(0, 5),
            gyro_y=rng.gauss(0, 5),
            gyro_z=rng.gauss(0, 5),
        )

        return SensorData(
            timestamp=datetime.now().isoformat(),
            bpm=bpm, stress=stress, sleep=sleep, spo2=spo2, mood=mood,
            imu=imu, temperature=36.5 + rng.gauss(0, 0.2),
        )

    def start_streaming(self, callback: Callable[[SensorData], None]):
        self.streaming = True
        while self.streaming:
            callback(self.read_sensors())
            time.sleep(1.0)

    def stop_streaming(self):
        self.streaming = False

    def get_seeded_history(self, metric: str, hours: int = 24) -> list:
        base_seed = hash(self.device_id) % (2**31)
        base_val = {"bpm": 72, "stress": 35, "sleep": 7, "spo2": 97, "mood_score": 5}.get(metric, 50)
        values = []
        for i in range(hours):
            rng = random.Random(base_seed + i * 1000)
            variation = rng.gauss(0, base_val * 0.12)
            val = max(0, min(100, base_val + variation))
            if metric == "sleep":
                val = max(0, min(10, base_val + rng.gauss(0, 1.5)))
            values.append(round(val, 1))
        return values


# ── Global instance (backward compat) ────────────────────

_default_ring = SimulatedRing()


def get_ring_data(username: str, intensity: float = 1.0) -> dict:
    _default_ring.device_id = username
    return _default_ring.read_sensors(intensity).to_dict()


def get_seeded_history(username: str, metric: str, hours: int = 24) -> list:
    _default_ring.device_id = username
    return _default_ring.get_seeded_history(metric, hours)


def get_ring_data_source() -> RingDataSource:
    return _default_ring


def set_ring_data_source(source: RingDataSource):
    global _default_ring
    _default_ring = source