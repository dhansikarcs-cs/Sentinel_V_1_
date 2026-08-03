"""BLE GATT ring source for OEM rings.

OEM rings (e.g. the Jport unit) typically expose a custom BLE service. The
vendor spec lists the service UUID, per-metric characteristic UUIDs, and the
byte format. Until that spec arrives, this adapter ships with:

  * the standard Heart Rate Measurement parser (BLE service 0x180D / 0x2A37),
  * a configurable characteristic map + per-characteristic parser hook,
  * a battery read via the standard battery service (0x180F / 0x2A19),
  * a subclass override point (`parse_characteristic`) for proprietary blobs.

Usage (once UUIDs + byte formats are known):

    source = BLEGATTRingSource(
        device_id="RING-OEM-001",
        address="<MAC>",
        char_map={
            "00002a37-0000-1000-8000-00805f9b34fb": "hrm",   # standard HR notify
            "<custom-hrv-uuid>": "hrv",
            "<custom-stress-uuid>": "stress",
        },
        parser={
            "<custom-hrv-uuid>": uint8,
            "<custom-stress-uuid>": uint8,
        },
    )

Requires `bleak` — install with:
    pip install -r backend/requirements-bridge.txt
"""

from typing import Callable, Dict, Optional

from app.services.ring.base import RingSource, SensorData

try:  # bleak is optional for the core app; the bridge needs it.
    from bleak import BleakClient

    _BLEAK_AVAILABLE = True
except ImportError:
    _BLEAK_AVAILABLE = False

# Standard UUIDs
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"
HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"


def uint8(data: bytes) -> int:
    return data[0] if data else 0


def uint16_le(data: bytes) -> int:
    return int.from_bytes(data[:2], "little")


def parse_hrm(data: bytes) -> dict:
    """Parse a standard BLE Heart Rate Measurement value."""
    if not data:
        return {"bpm": 0}
    flags = data[0]
    if flags & 0x01:
        bpm = int.from_bytes(data[1:3], "little")
    else:
        bpm = data[1]
    return {"bpm": bpm}


class BLEGATTRingSource(RingSource):
    name = "ble_gatt"

    def __init__(
        self,
        device_id: str = "",
        address: str = "",
        char_map: Optional[Dict[str, str]] = None,
        parser: Optional[Dict[str, Callable[[bytes], dict]]] = None,
        battery_uuid: str = BATTERY_LEVEL,
        client: Optional["BleakClient"] = None,
    ):
        if not address and not device_id:
            raise ValueError("BLEGATTRingSource needs a BLE address or device_id")
        self.device_id = device_id or f"ble_{address}"
        self.address = address
        self.char_map = char_map or {}
        self.parser = parser or {}
        self.battery_uuid = battery_uuid
        self._client = client
        self._connected = False

    def _require_bleak(self):
        if not _BLEAK_AVAILABLE:
            raise RuntimeError(
                "bleak is not installed. Run: pip install -r backend/requirements-bridge.txt"
            )

    def connect(self) -> bool:
        self._require_bleak()
        if not self._connected:
            if self._client is None:
                self._client = BleakClient(self.address)
            import asyncio

            asyncio.run(self._client.connect())
            self._connected = True
        return True

    def disconnect(self) -> None:
        if self._connected and self._client is not None:
            import asyncio

            asyncio.run(self._client.disconnect())
            self._connected = False

    def _read_characteristic(self, uuid: str) -> bytes:
        import asyncio

        return asyncio.run(self._client.read_gatt_char(uuid))

    def parse_characteristic(self, uuid: str, data: bytes) -> dict:
        """Override for proprietary byte blobs. Defaults to the parser map,
        then a standard HRM parse for the HR measurement characteristic."""
        if uuid in self.parser:
            return self.parser[uuid](data)
        if uuid == HEART_RATE_MEASUREMENT:
            return parse_hrm(data)
        return {}

    def read_sensors(self) -> SensorData:
        if not self._connected:
            self.connect()
        reading: dict = {}
        for uuid, metric in self.char_map.items():
            raw = self._read_characteristic(uuid)
            parsed = self.parse_characteristic(uuid, raw)
            if metric in ("bpm", "hrv", "stress", "spo2", "sleep_hours"):
                reading[metric] = parsed.get(metric, 0)
            else:
                reading.update(parsed)
        battery = 0
        try:
            raw_battery = self._read_characteristic(self.battery_uuid)
            battery = uint8(raw_battery)
        except Exception:
            pass
        reading["battery"] = battery
        return SensorData.from_dict(reading, device_id=self.device_id)
