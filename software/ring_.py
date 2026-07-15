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


# ── Hardware SDK / API Connectivity Layer ──────────────
#
# To connect a real ring device, either:
#   1. Implement RingDataSource and call set_ring_data_source()
#   2. Or run the HTTP API server and push data via POST
#
# Example: from your hardware's SDK, call:
#   POST http://localhost:9090/api/ring-data
#   {"bpm": 85, "stress": 45, "spo2": 97, "sleep": 6.5, "mood": "calm", ...}

if not hasattr(SensorData, "from_dict"):
    def _from_dict(cls, data: dict):
        ts = data.get("timestamp", datetime.now().isoformat())
        imu_data = data.get("imu", {})
        imu = IMUData(
            accel_x=imu_data.get("accel_x", 0.0),
            accel_y=imu_data.get("accel_y", 0.0),
            accel_z=imu_data.get("accel_z", 0.0),
            gyro_x=imu_data.get("gyro_x", 0.0),
            gyro_y=imu_data.get("gyro_y", 0.0),
            gyro_z=imu_data.get("gyro_z", 0.0),
            mag_x=imu_data.get("mag_x", 0.0),
            mag_y=imu_data.get("mag_y", 0.0),
            mag_z=imu_data.get("mag_z", 0.0),
        )
        return SensorData(
            timestamp=ts,
            bpm=data.get("bpm", 72),
            stress=data.get("stress", 35),
            sleep=data.get("sleep", 7.0),
            spo2=data.get("spo2", 97.0),
            mood=data.get("mood", "neutral"),
            imu=imu,
            temperature=data.get("temperature", 36.5),
        )
    SensorData.from_dict = classmethod(_from_dict)


_HARDWARE_BUFFER: dict[str, SensorData] = {}
_HARDWARE_LOCK = __import__("threading").Lock()


def push_hardware_data(device_id: str, data: dict):
    """Thread-safe push of ring data from external hardware SDK/API.

    Call this from your hardware SDK callback or HTTP endpoint
    to inject live sensor readings into the app.
    """
    sd = SensorData.from_dict(data)
    with _HARDWARE_LOCK:
        _HARDWARE_BUFFER[device_id] = sd


class HardwareRingDataSource(RingDataSource):
    """RingDataSource that reads from the hardware buffer.

    Swap this in with set_ring_data_source(HardwareRingDataSource())
    to pipe real device data through the existing app.
    """
    def __init__(self):
        self.device_id = ""
        self.streaming = False
        self._fallback = SimulatedRing()

    def connect(self, device_id: str) -> bool:
        self.device_id = device_id
        return True

    def disconnect(self):
        self.streaming = False

    def read_sensors(self, intensity: float = 1.0) -> SensorData:
        with _HARDWARE_LOCK:
            sd = _HARDWARE_BUFFER.get(self.device_id)
        if sd is not None:
            return sd
        return self._fallback.read_sensors(intensity)

    def start_streaming(self, callback: Callable[[SensorData], None]):
        self.streaming = True
        while self.streaming:
            data = self.read_sensors()
            callback(data)
            time.sleep(1.0)

    def stop_streaming(self):
        self.streaming = False


# ── HTTP API Server for Hardware Data (standalone) ─────

def run_ring_api_server(host: str = "0.0.0.0", port: int = 9090):
    """Start an HTTP server that accepts hardware data via POST.

    Your ring device (or its SDK) can call:
        POST http://<host>:<port>/api/ring-data
        Content-Type: application/json
        {"device_id": "cel", "bpm": 85, "stress": 45, ...}

    This is a lightweight thread-per-request server. For production,
    use a proper WSGI server or integrate with the main app.
    """
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json as _json
    except ImportError:
        print("http.server not available — cannot start API server")
        return

    class _RingAPIHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload = _json.loads(body)
                device_id = payload.pop("device_id", "default")
                push_hardware_data(device_id, payload)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(_json.dumps({"status": "ok", "device_id": device_id}).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(_json.dumps({"status": "error", "error": str(e)}).encode())

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with _HARDWARE_LOCK:
                devices = list(_HARDWARE_BUFFER.keys())
            self.wfile.write(__import__("json").dumps({
                "status": "ok",
                "devices": devices,
                "endpoints": {
                    "POST /api/ring-data": "Push sensor data",
                    "GET /api/health": "Health check",
                },
                "notes": "Send POST with device_id + sensor fields. See SensorData dataclass for all fields."
            }).encode())

        def log_message(self, fmt, *args):
            print(f"[RingAPI] {args[0]} {args[1]} {args[2]}")

    server = HTTPServer((host, port), _RingAPIHandler)
    print(f"[RingAPI] Server listening on http://{host}:{port}")
    print(f"[RingAPI] POST /api/ring-data — push hardware sensor data")
    print(f"[RingAPI] GET  /api/health   — health check")
    print(f"[RingAPI] To use: from your ring SDK, send JSON to /api/ring-data")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[RingAPI] Shutting down.")
        server.server_close()