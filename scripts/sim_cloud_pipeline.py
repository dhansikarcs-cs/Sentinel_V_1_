"""cloud-pipeline survival simulation.

Ring emulator -> (simulated Secure Transport Layer: store-and-forward queue)
               -> POST /ring/data.

The emulator normally talks straight to the dashboard endpoint; in real life a
cloud transport sits between device and backend. This simulates that transport
with the behaviours the STL design (transport.md) mandates:

  * latency + jitter (reordering)
  * at-least-once delivery (duplicate injection)
  * transient forwarding failures -> keep + retry (store-and-forward)
  * HTTP 429 handling (with/without Retry-After)
  * backend downtime (connection refused) -> exponential backoff, never drop
  * offline-buffer burst drain on reconnect
  * device-clock skew forwarded in the payload

Afterwards it verifies survival end-to-end against the backend DB: every unique
sample must land exactly once (the backend dedupes at-least-once replays by
(device_id, seq) and stores the raw envelope), and any loss is reported. It is
scripted, so it doubles as a regression check.

Usage:  python scripts/sim_cloud_pipeline.py [--base URL] [--samples N]
"""

import argparse
import os
import random
import sqlite3
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.ring import SensorData, SimulatedRing  # noqa: E402  (sys.path bootstrap above)

TAG = uuid.uuid4().hex[:6]
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}".rstrip())


def api(base):
    return base.rstrip("/") + "/api"


class CloudTransport:
    """Store-and-forward queue that behaves like the STL mock."""

    def __init__(
        self,
        base,
        serial,
        token,
        latency=(0.05, 1.8),
        dup_rate=0.15,
        drop_rate=0.10,
        max_attempts=30,
        clock_skew_s=0.0,
    ):
        self.base = api(base)
        self.serial = serial
        self.token = token
        self.latency = latency
        self.dup_rate = dup_rate
        self.drop_rate = drop_rate
        self.max_attempts = max_attempts
        self.clock_skew_s = clock_skew_s
        self.queue = []  # items under delivery (hold-back list)
        self.pending = []  # items waiting for deliver_at
        self.seq = 0
        self.stats = {
            "unique_samples": 0,
            "accepted_attempts": 0,
            "accepted_ids": [],
            "transient_retries": 0,
            "duplicates_injected": 0,
            "rate_limited": 0,
            "retry_after_seen": 0,
            "backend_down": 0,
            "permanently_rejected": 0,
            "dead_lettered": 0,
            "attempts": 0,
        }
        self._headers = {"X-Device-Serial": serial, "X-Device-Token": token}

    # ── device side ──────────────────────────────────────────────────────────
    def enqueue(self, sample: SensorData):
        self.seq += 1
        ts = datetime.now(UTC) + timedelta(seconds=self.clock_skew_s)
        payload = {
            "device_id": self.serial,
            "bpm": int(sample.bpm),
            "stress": int(sample.stress),
            "sleep_hours": float(sample.sleep_hours),
            "spo2": float(sample.spo2),
            "hrv": int(sample.hrv),
            "seq": self.seq,  # cloud envelope metadata; the backend dedupes on (device_id, seq)
            "timestamp": ts.isoformat(),
        }
        self.stats["unique_samples"] += 1
        # device keeps its own copy until ACK (transport constitution #5 / §3.1)
        item = {
            "payload": payload,
            "attempts": 0,
            "deliver_at": time.monotonic() + random.uniform(*self.latency),
            "seq": self.seq,
        }
        self.pending.append(item)
        # at-least-once: the STL may hold a second copy ("delivery twice")
        if random.random() < self.dup_rate:
            self.stats["duplicates_injected"] += 1
            self.pending.append(
                {
                    "payload": payload,
                    "attempts": 0,
                    "deliver_at": item["deliver_at"] + random.uniform(0.2, 1.0),
                    "seq": self.seq,
                }
            )
        return item

    # ── transport side ───────────────────────────────────────────────────────
    def drain(self):
        """Advance time: move due items into delivery, attempt sends."""
        now = time.monotonic()
        ready = [it for it in self.pending if it["deliver_at"] <= now]
        self.pending = [it for it in self.pending if it["deliver_at"] > now]
        for item in ready:
            self._attempt(item)

    def _attempt(self, item):
        item["attempts"] += 1
        self.stats["attempts"] += 1
        # transient forwarding failure at the STL (store-and-forward retry)
        if random.random() < self.drop_rate:
            self.stats["transient_retries"] += 1
            item["deliver_at"] = time.monotonic() + random.uniform(0.5, 2.0)
            self.pending.append(item)
            if item["attempts"] >= self.max_attempts:
                self.stats["dead_lettered"] += 1
            return
        try:
            r = requests.post(
                f"{self.base}/ring/data",
                headers=self._headers,
                json=item["payload"],
                timeout=10,
            )
        except requests.RequestException:
            # backend down / network edge → backoff and keep the copy
            self.stats["backend_down"] += 1
            item["deliver_at"] = time.monotonic() + random.uniform(1.0, 4.0)
            self.pending.append(item)
            if item["attempts"] >= self.max_attempts:
                self.stats["dead_lettered"] += 1
            return

        if r.status_code == 200:
            self.stats["accepted_attempts"] += 1
            body = r.json()
            if isinstance(body, dict) and body.get("id"):
                self.stats["accepted_ids"].append(body["id"])
            return

        if r.status_code == 429:
            self.stats["rate_limited"] += 1
            cap = r.headers.get("Retry-After")
            if cap:
                self.stats["retry_after_seen"] += 1
                wait = float(cap)
            else:
                wait = random.uniform(2.0, 5.0)
            item["deliver_at"] = time.monotonic() + wait
            self.pending.append(item)
            if item["attempts"] >= self.max_attempts:
                self.stats["dead_lettered"] += 1
            return

        # any other 4xx/5xx that we don't auto-retry
        self.stats["permanently_rejected"] += 1

    def outstanding(self):
        return len(self.pending) + len(self.queue)

    def drain_all(self, deadline_s):
        end = time.monotonic() + deadline_s
        while self.pending and time.monotonic() < end:
            self.drain()
            time.sleep(0.05)


def panic_backend(base_url, after_s, duration_s):
    """Deterministically kill and relaunch the backend to test outage survival."""
    import subprocess
    import threading
    from urllib.parse import urlparse

    port = urlparse(base_url).port or 8000
    host = urlparse(base_url).hostname or "127.0.0.1"

    def _find_pid():
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, check=False
        ).stdout
        for line in out.splitlines():
            part = line.split()
            if f"{host}:{port}" in part and "LISTENING" in line:
                return part[-1]
        return None

    def _run():
        time.sleep(after_s)
        pid = _find_pid()
        if pid:
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, check=False)
            print(f"[panic] killed backend pid {pid}; down for {duration_s}s", flush=True)
        else:
            print("[panic] no backend listener found on port", port, flush=True)
        time.sleep(duration_s)
        env = dict(os.environ)
        env["JWT_SECRET"] = "sep-strong-" + uuid.uuid4().hex
        env["ENCRYPTION_REQUIRED"] = "false"
        env["DATABASE_URL"] = f"sqlite:///{BACKEND / 'data' / 'sentinel.db'}"
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
            cwd=str(BACKEND),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        print("[panic] backend relaunched", flush=True)

    threading.Thread(target=_run, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--clock-skew-s", type=float, default=0.0)
    ap.add_argument("--burst", type=int, default=0, help="extra samples queued instantly (offline-buffer drain)")
    ap.add_argument("--db", default=str(BACKEND / "data" / "sentinel.db"))
    ap.add_argument("--drain-time", type=float, default=25.0, help="max seconds to keep draining the transport queue")
    ap.add_argument("--hold-secs", type=float, default=0.0, help="hold the queue before draining (lets an external outage begin)")
    ap.add_argument("--buffered", action="store_true", help="accumulate all samples offline, then deliver in one burst")
    ap.add_argument("--panic-after-secs", type=float, default=0.0, help="kill the backend this many seconds into the run")
    ap.add_argument("--panic-duration", type=float, default=0.0, help="keep the backend dead for this long, then relaunch it")
    args = ap.parse_args()

    base = api(args.base)
    uname = f"cl_{TAG}"
    serial = f"CLOUD-{TAG}"

    # ── setup: provision patient, pair a device ──────────────────────────────
    r = requests.post(
        f"{base}/auth/register",
        json={
            "username": uname,
            "password": "Str0ng!Pass1",
            "name": "Cloud Pipeline Sim",
            "role": "patient",
            "age": 31,
            "occupation": "Tester",
            "clinic_code": "SENTINEL-TEST",
        },
        timeout=30,
    )
    check("register throwaway patient", r.status_code == 200, r.text[:100])
    login = requests.post(f"{base}/auth/login", json={"username": uname, "password": "Str0ng!Pass1"}, timeout=30).json()
    jwt = login.get("access_token", "")
    pair = requests.post(
        f"{base}/ring/pair",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"serial": serial, "vendor": "simulated"},
        timeout=30,
    ).json()
    token = pair.get("token", "")
    check("device paired, token issued once", bool(token))

    transport = CloudTransport(args.base, serial, token, clock_skew_s=args.clock_skew_s)
    ring = SimulatedRing(username=uname, device_id=serial, scenario="stressed")
    ring.connect()

    # ── produce samples through the transport ────────────────────────────────
    print(f"\n-- streaming {args.samples} unique samples through simulated cloud --")
    for i in range(args.samples):
        transport.enqueue(ring.read_sensors())
        time.sleep(args.interval)
        if i % 5 == 4 and not args.buffered:
            transport.drain_all(1.5)
    if args.burst > 0:
        print(f"-- reconnect burst: draining {args.burst} buffered samples at once --")
        for _ in range(args.burst):
            transport.enqueue(ring.read_sensors())
    if args.hold_secs > 0:
        print(f"-- transport holding {transport.outstanding()} queued samples for {args.hold_secs}s --")
        time.sleep(args.hold_secs)
    if args.panic_after_secs > 0 and args.panic_duration > 0:
        panic_backend(args.base, args.panic_after_secs, args.panic_duration)
        time.sleep(args.panic_after_secs + 1.0)  # let the kill land before we drain
    # give the transport time to empty; outer harness may bounce the backend here
    transport.drain_all(args.burst * 1.0 + args.drain_time)

    s = transport.stats
    print("\n-- transport statistics --")
    for k, v in s.items():
        print(f"  {k:22s} {v}")

    # ── verify against the backend's own store ──────────────────────────────
    db = sqlite3.connect(args.db)
    rows = db.execute(
        "select id, device_id, seq from ring_sensor_log where device_id = ? order by id",
        (serial,),
    ).fetchall()
    accepted = s["accepted_attempts"]
    unique = s["unique_samples"]
    # The transport delivers at-least-once (retries + injected duplicates carry
    # the same seq). Server-side idempotency must collapse them to one row each.
    seqs = [r[2] for r in rows]
    distinct = len(set(seqs))
    dup_by_seq = len(seqs) - distinct
    check(
        "every delivered seq stored exactly once (server dedupe)",
        distinct == unique and dup_by_seq == 0 and len(rows) >= unique,
        f"rows={len(rows)} distinct_seq={distinct} unique={unique} dup_by_seq={dup_by_seq} accepted={accepted}",
    )
    check("no unique sample lost", len(rows) >= unique, f"unique={unique} stored={len(rows)}")
    check("no dead-lettered samples", s["dead_lettered"] == 0, f"dl={s['dead_lettered']}")
    check("no permanently rejected", s["permanently_rejected"] == 0, f"rej={s['permanently_rejected']}")

    raw = db.execute(
        "select raw_json from ring_sensor_log where device_id = ? and seq is not null limit 1",
        (serial,),
    ).fetchone()
    check(
        "raw envelope stored at rest (hash-chain carrier)",
        bool(raw and raw[0] and '"seq"' in str(raw[0])),
        "raw_json populated" if raw and raw[0] else "raw_json empty",
    )

    # dashboard-facing reads must stay correct despite skew/ordering.
    # If a panic rotated the JWT secret, sessions are invalidated (by design) -
    # a real client would simply log in again, so mirror that here.
    _jwt = jwt
    if args.panic_after_secs > 0 and args.panic_duration > 0:
        _jwt = login.get("access_token", "")  # stale after secret rotation
        retry_login = requests.post(
            f"{base}/auth/login", json={"username": uname, "password": "Str0ng!Pass1"}, timeout=10
        )
        if retry_login.status_code == 200:
            _jwt = retry_login.json().get("access_token", "")
    well = requests.get(
        f"{base}/patients/me/wellness",
        headers={"Authorization": f"Bearer {_jwt}"},
        timeout=10,
    )
    latest_ok = False
    if well.status_code == 200 and isinstance(well.json(), dict):
        wr = well.json().get("data") or well.json()
        ring_part = wr.get("ring") or wr
        latest_ok = bool(ring_part.get("bpm"))
    check("wellness returns a latest ring summary", latest_ok, str(well.status_code))

    # out-of-range never survives (bpm in 30..250)
    bad = db.execute(
        "select count(*) from ring_sensor_log where device_id = ? and (bpm > 250 or bpm < 30 or hrv > 300 or hrv < 0 or spo2 > 100 or spo2 < 50 or stress > 100 or stress < 0)",
        (serial,),
    ).fetchone()[0]
    check("no out-of-range rows persisted", bad == 0, f"bad={bad}")

    total = sum(1 for _, ok in RESULTS if ok)
    print(f"\nCLOUD-PIPELINE SIM: {total}/{len(RESULTS)} checks passed")
    return int(total != len(RESULTS))


if __name__ == "__main__":
    sys.exit(main())
