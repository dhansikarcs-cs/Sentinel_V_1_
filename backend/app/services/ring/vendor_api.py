"""Vendor SDK/API ring adapter.

Consumer rings (Oura, Ultrahuman, Circular, ...) expose vendor SDKs or REST
APIs. Subclass this and implement `_fetch()` (or pass a `fetch_fn`), then push
the returned `SensorData` into Sentinel's `POST /ring/data` endpoint.

Example:

    class OuraSource(VendorAPIRingSource):
        def _fetch(self):
            payload = oura_sdk.get_recent_sleep_activity()
            return {
                "bpm": payload["hr"]["average"],
                "stress": payload["stress"]["level"],
                "hrv": payload["hrv"]["rmssd"],
            }
"""

from typing import Callable, Optional

from app.services.ring.base import RingSource, SensorData


class VendorAPIRingSource(RingSource):
    name = "vendor_api"

    def __init__(
        self,
        device_id: str,
        fetch_fn: Optional[Callable[[], dict]] = None,
        access_token: str = "",
    ):
        self.device_id = device_id
        self._fetch_fn = fetch_fn
        self.access_token = access_token
        self._connected = False

    def connect(self) -> bool:
        if not self.access_token and not self._fetch_fn:
            raise RuntimeError(
                "VendorAPIRingSource needs an access_token or a fetch_fn to authenticate"
            )
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def read_sensors(self) -> SensorData:
        if not self._connected:
            self.connect()
        raw = self._fetch_fn() if self._fetch_fn else self._fetch()
        return SensorData.from_dict(raw, device_id=self.device_id)

    def _fetch(self) -> dict:
        """Override with the vendor SDK/API call. Must return a dict of sensor fields."""
        raise NotImplementedError(
            "Implement _fetch() in a VendorAPIRingSource subclass, or pass fetch_fn"
        )
