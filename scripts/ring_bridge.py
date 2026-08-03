"""Ring bridge: read from any RingSource and push to Sentinel's /ring/data.

Interface-agnostic — the same loop works for simulated, BLE GATT, or vendor
cloud sources. Configure a source via --source and the matching args, or
subclass/import a custom one.

Auth uses the device-token path (X-Device-Serial + X-Device-Token), so a ring
never needs a patient password.

Examples:
  # Simulated (demo):
  python scripts/ring_bridge.py --source simulated --username alaya --scenario stressed --interval 30
  # BLE (once the Jport spec arrives + bleak installed):
  python scripts/ring_bridge.py --source ble --device RING-OEM-001 --address AA:BB:CC:DD:EE:FF --token <tok>
  # Vendor cloud (once the SDK/API is known):
  python scripts/ring_bridge.py --source vendor --device RING-OEM-001 --token <tok>
"""

import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DEFAULT_API = "http://localhost:8000/api"


def _request(method, url, headers=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = dict(headers or {})
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def login(base, username, password):
    return _request("POST", f"{base}/auth/login", body={"username": username, "password": password})


def push(base, sd, serial, device_token):
    headers = {"X-Device-Serial": serial, "X-Device-Token": device_token}
    return _request("POST", f"{base}/ring/data", headers=headers, body=sd.to_dict())


def build_source(args):
    if args.source == "simulated":
        from app.services.ring import SimulatedRing
        return SimulatedRing(username=args.username, device_id=args.device, scenario=args.scenario)
    if args.source == "ble":
        from app.services.ring import BLEGATTRingSource
        char_map = {}
        parser = {}
        if args.hrm_uuid:
            char_map[args.hrm_uuid] = "hrm"
        if args.hrv_uuid:
            char_map[args.hrv_uuid] = "hrv"
        if args.stress_uuid:
            char_map[args.stress_uuid] = "stress"
        return BLEGATTRingSource(device_id=args.device, address=args.address, char_map=char_map, parser={})
    if args.source == "vendor":
        from app.services.ring import VendorAPIRingSource
        return VendorAPIRingSource(device_id=args.device, fetch_fn=None, access_token=args.vendor_token)
    raise SystemExit(f"Unknown source '{args.source}' (choose: simulated | ble | vendor)")


def main():
    ap = argparse.ArgumentParser(description="Sentinel ring bridge")
    ap.add_argument("--api", default=os.environ.get("SENTINEL_API", DEFAULT_API))
    ap.add_argument("--source", choices=["simulated", "ble", "vendor"], required=True)
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--device", default="", help="device serial (must be paired)")
    ap.add_argument("--token", default=os.environ.get("SENTINEL_DEVICE_TOKEN", ""), help="device token")
    ap.add_argument("--username", default="", help="simulated source: patient username")
    ap.add_argument("--password", default="", help="simulated source: patient password (for pairing)")
    ap.add_argument("--scenario", default="balanced")
    ap.add_argument("--address", default="", help="ble source: MAC address")
    ap.add_argument("--hrm-uuid", default="", help="ble source: HR measurement char UUID")
    ap.add_argument("--hrv-uuid", default="")
    ap.add_argument("--stress-uuid", default="")
    ap.add_argument("--vendor-token", default="", help="vendor cloud OAuth token")
    args = ap.parse_args()

    serial = args.device
    device_token = args.token

    if args.source == "simulated" and args.username and not serial:
        login_resp = login(args.api, args.username, args.password)
        jwt = login_resp["access_token"]
        serial = f"ring_{args.username}"
        if not device_token:
            from app.services.ring import SimulatedRing  # noqa: F401
            paired = _request("POST", f"{args.api}/ring/pair", headers={"Authorization": f"Bearer {jwt}"}, body={"serial": serial, "vendor": "simulated"})
            device_token = paired["token"]
            print(f"[pair] device {serial} paired, token issued")

    if not serial or not device_token:
        raise SystemExit("Need --device + --token (device-token path), or --username/--password (auto-pair)")

    source = build_source(args)
    source.connect()
    print(f"[bridge] {source.name} -> {args.api}/ring/data  (every {args.interval}s)")

    while True:
        sd = source.read_sensors()
        try:
            resp = push(args.api, sd, serial, device_token)
            print(f"[push] bpm={sd.bpm} stress={sd.stress} hrv={sd.hrv} sleep={sd.sleep_hours} spo2={sd.spo2} -> id={resp['id']}")
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
