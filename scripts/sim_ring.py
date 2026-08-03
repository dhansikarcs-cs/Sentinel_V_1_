"""Stream simulated ring data into a running Sentinel backend.

Two auth modes:
  --token   device token (hardware path; requires the device paired first)
  --username/--password   patient JWT (simulated-from-portal path)

The device-token path is the one real hardware will use.

Examples:
  python scripts/sim_ring.py --username alaya --password 4321 --scenario stressed
  python scripts/sim_ring.py --device RING-DEMO-001 --token <tok> --scenario calm --interval 30
"""

import argparse
import os
import sys
import time
import urllib.request
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.ring import SimulatedRing  # noqa: E402

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


def pair_device(base, token, serial, vendor="simulated"):
    headers = {"Authorization": f"Bearer {token}"}
    return _request("POST", f"{base}/ring/pair", headers=headers, body={"serial": serial, "vendor": vendor})


def push(base, data, serial=None, device_token=None, jwt=None):
    headers = {}
    if serial and device_token:
        headers["X-Device-Serial"] = serial
        headers["X-Device-Token"] = device_token
    elif jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    return _request("POST", f"{base}/ring/data", headers=headers, body=data.to_dict())


def main():
    ap = argparse.ArgumentParser(description="Simulated ring data streamer")
    ap.add_argument("--api", default=os.environ.get("SENTINEL_API", DEFAULT_API))
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="balanced")
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--once", action="store_true", help="push a single reading and exit")
    ap.add_argument("--device", default="", help="paired device serial (hardware path)")
    ap.add_argument("--token", default=os.environ.get("SENTINEL_DEVICE_TOKEN", ""), help="device token")
    ap.add_argument("--username", default="")
    ap.add_argument("--password", default="")
    args = ap.parse_args()

    serial = args.device
    device_token = args.token

    if not serial and args.username:
        login_resp = login(args.api, args.username, args.password)
        jwt = login_resp["access_token"]
        serial = f"ring_{args.username}"
        if not device_token:
            paired = pair_device(args.api, jwt, serial)
            device_token = paired["token"]
            print(f"[pair] device {serial} paired, token issued")

    ring = SimulatedRing(username=args.username or serial, device_id=serial, scenario=args.scenario)
    ring.connect()
    print(f"[sim] {ring.name} / {ring.scenario} -> {args.api}/ring/data  (every {args.interval}s)")

    while True:
        sd = ring.read_sensors()
        resp = push(args.api, sd, serial=serial, device_token=device_token)
        print(f"[push] bpm={sd.bpm} stress={sd.stress} hrv={sd.hrv} sleep={sd.sleep_hours} spo2={sd.spo2} -> id={resp['id']}")
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    from app.services.ring import SCENARIOS
    main()
