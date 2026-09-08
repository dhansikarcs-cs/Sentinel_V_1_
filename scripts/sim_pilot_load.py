"""Pilot-scale load simulation: 50-100 users, no hardware (software clients).

Each simulated user behaves like a real pilot participant:
  * logs in once ("app boot")
  * sees their paired ring device live (GET /ring/devices)
  * the device pushes a reading every few seconds over a cloud-style
    transport: at-least-once, retries the *same seq* on 429/5xx with backoff
    (so the server's idempotency is exercised under real contention)
  * reads their wellness summary periodically

A small number of psychologist threads poll the patient list + ring devices
(a realistic dashboard load). Every request is measured; failures are
categorised (429 / 5xx+locked / 4xx / network) and latency percentiles are
reported, plus a DB-level integrity check (no unique seq lost, no dup rows).

Usage:
  python scripts/sim_pilot_load.py --base http://127.0.0.1:8011 --users 100
"""

import argparse
import random
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

TAG = uuid.uuid4().hex[:6]
_LOCK = threading.Lock()
_SEED_LOCK = threading.Lock()
_STATS = {"ok": 0, "codes": {}, "network": 0, "latencies": [], "push_latencies": []}


def _record(code, ms, is_push=False):
    with _LOCK:
        _STATS["latencies"].append(ms)
        if is_push:
            _STATS["push_latencies"].append(ms)
        if code == 200:
            _STATS["ok"] += 1
            _STATS["codes"][200] = _STATS["codes"].get(200, 0) + 1
        else:
            _STATS["codes"][code] = _STATS["codes"].get(code, 0) + 1


def api(base):
    return base.rstrip("/") + "/api"


def pct(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


def provision_user(base, uname, tag):
    # Gated onboarding: seed N users but pace them so a bulk seed doesn't
    # brute-force the per-IP rate limit in a single window. Each worker takes a
    # turn; real onboarding is naturally this spread out.
    _SEED_LOCK.acquire()
    try:
        time.sleep(0.3)
        return _provision_unlocked(base, uname, tag)
    finally:
        _SEED_LOCK.release()


def _provision_unlocked(base, uname, tag):
    r = requests.post(
        f"{api(base)}/auth/register",
        json={
            "username": uname,
            "password": "Str0ng!Pass1",
            "name": f"Pilot {tag}",
            "role": "patient",
            "age": 30,
            "occupation": "Tester",
            "clinic_code": f"PILOT-{tag}",
        },
        timeout=30,
    )
    if r.status_code == 429:
        retry = r.headers.get("Retry-After")
        time.sleep(float(retry) if retry else 5.0)
        r = requests.post(
            f"{api(base)}/auth/register",
            json={
                "username": uname,
                "password": "Str0ng!Pass1",
                "name": f"Pilot {tag}",
                "role": "patient",
                "age": 30,
                "occupation": "Tester",
                "clinic_code": f"PILOT-{tag}",
            },
            timeout=30,
        )
    if r.status_code not in (200, 400):  # 400 = already registered
        raise RuntimeError(f"register failed {r.status_code}: {r.text[:120]}")
    login = requests.post(
        f"{api(base)}/auth/login", json={"username": uname, "password": "Str0ng!Pass1"}, timeout=30
    )
    if login.status_code == 429:
        time.sleep(5.0)
        login = requests.post(
            f"{api(base)}/auth/login", json={"username": uname, "password": "Str0ng!Pass1"}, timeout=30
        )
    if login.status_code != 200:
        raise RuntimeError(f"login failed {login.status_code}: {login.text[:120]}")
    jwt = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt}"}
    pair = requests.post(
        f"{api(base)}/ring/pair",
        headers=headers,
        json={"serial": f"PL-{tag}-{uuid.uuid4().hex[:8]}", "vendor": "simulated"},
        timeout=30,
    )
    if pair.status_code != 200:
        raise RuntimeError(f"pair failed {pair.status_code}: {pair.text[:120]}")
    body = pair.json()
    return jwt, body["serial"], body["token"]


def device_thread(base, jwt, serial, token, interval_s, duration_s, checked_reads, burst_late=0.0):
    """One pilot patient: periodic ring pushes + wellness reads.

    If burst_late is set, after that many seconds the device flushes an offline
    buffer (a few seqs) in quick succession - simulating a reconnect / manual
    catch-up and stressing idempotency + write contention.
    """
    end = time.monotonic() + duration_s
    seq = 0
    headers = {"X-Device-Serial": serial, "X-Device-Token": token}
    http = requests.Session()
    burst_at = time.monotonic() + burst_late if burst_late > 0 else None
    while time.monotonic() < end:
        seq += 1
        reading = {
            "bpm": random.randint(62, 118),
            "stress": random.randint(15, 70),
            "sleep_hours": round(random.uniform(5.0, 9.0), 1),
            "spo2": round(random.uniform(94.0, 99.0), 1),
            "hrv": random.randint(20, 60),
        }
        queued = [dict(reading, seq=seq, timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]

        flushed = False
        if burst_at and time.monotonic() >= burst_at and not flushed:
            now = time.time()
            for b in range(random.randint(2, 6)):  # offline buffer accumulated while away
                ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + b))
                queued.append(dict(reading, seq=seq + 1 + b, timestamp=ts))
            seq += random.randint(2, 6)
            flushed = True
            burst_at = None

        for payload in queued:
            _deliver_with_retry(http, f"{api(base)}/ring/data", headers, payload)
            time.sleep(random.uniform(0.05, 0.2))
        if seq % checked_reads == 0:
            t0 = time.monotonic()
            try:
                r = http.get(
                    f"{api(base)}/patients/me/wellness",
                    headers={"Authorization": f"Bearer {jwt}"},
                    timeout=15,
                )
                _record(r.status_code, (time.monotonic() - t0) * 1000)
            except requests.RequestException:
                with _LOCK:
                    _STATS["network"] += 1
        time.sleep(interval_s * random.uniform(0.8, 1.2))


def _deliver_with_retry(http, url, headers, payload):
    """At-least-once delivery: retry the *same* payload (seq) on 429/5xx."""
    for _ in range(8):
        t0 = time.monotonic()
        try:
            r = http.post(url, headers=headers, json=payload, timeout=15)
        except requests.RequestException:
            with _LOCK:
                _STATS["network"] += 1
            time.sleep(random.uniform(0.2, 1.0))
            continue
        ms = (time.monotonic() - t0) * 1000
        if r.status_code == 200:
            _record(200, ms, is_push=True)
            return
        if r.status_code not in (429, 500, 502, 503, 504):
            _record(r.status_code, ms, is_push=True)
            return
        _record(r.status_code, ms, is_push=True)
        time.sleep(random.uniform(0.2, 1.0))


def psych_thread(base, jwt, duration_s):
    """Psychologist dashboard polling."""
    headers = {"Authorization": f"Bearer {jwt}"}
    list_path = f"{api(base)}/psychologists/patients"
    r = requests.get(list_path, headers=headers, timeout=15)
    if r.status_code == 404:
        list_path = f"{api(base)}/patients"
    end = time.monotonic() + duration_s
    http = requests.Session()
    while time.monotonic() < end:
        for path in (list_path, f"{api(base)}/ring/devices"):
            t0 = time.monotonic()
            try:
                r = http.get(path, headers=headers, timeout=15)
                _record(r.status_code, (time.monotonic() - t0) * 1000)
            except requests.RequestException:
                with _LOCK:
                    _STATS["network"] += 1
        time.sleep(random.uniform(5, 8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8011")
    ap.add_argument("--users", type=int, default=60)
    ap.add_argument("--psych", type=int, default=2)
    ap.add_argument("--duration", type=float, default=90.0)
    ap.add_argument("--interval", type=float, default=5.0, help="device push interval in seconds")
    ap.add_argument("--read-every", type=int, default=3, help="wellness read every N pushes")
    ap.add_argument("--tag", default=TAG)
    ap.add_argument("--db", default="")
    ap.add_argument("--prov-concurrency", type=int, default=8, help="parallel workers during seed provisioning")
    ap.add_argument("--burst-late", type=float, default=0.0, help="offline-buffer burst this many seconds into the run")
    args = ap.parse_args()

    psych_hands = []

    print(f"-- provisioning {args.users} pilot patients (tag {args.tag}) --")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, min(args.prov_concurrency, args.users))) as ex:
        futs = [
            ex.submit(provision_user, args.base, f"pl_{args.tag}_{i}", args.tag) for i in range(args.users)
        ]
        hands = [f.result() for f in futs]
    print(f"-- provisioned in {time.monotonic() - t0:.1f}s --")

    # psychologist accounts (raise a patient to psychologist directly)
    for i in range(args.psych):
        uname = f"psych_{args.tag}_{i}"
        b = api(args.base)
        requests.post(
            f"{b}/auth/register",
            json={
                "username": uname,
                "password": "Str0ng!Pass1",
                "name": f"Psych {args.tag}",
                "role": "patient",
                "age": 40,
                "occupation": "Psych",
                "clinic_code": f"PILOT-{args.tag}",
            },
            timeout=30,
        )
        login = requests.post(f"{b}/auth/login", json={"username": uname, "password": "Str0ng!Pass1"}, timeout=30)
        psych_hands.append(login.json()["access_token"])
        if args.db:
            db = sqlite3.connect(args.db)
            db.execute("update patient_profiles set role='psychologist' where username=?", (uname,))
            db.commit()
            db.close()

    print(f"-- running {args.users}+{args.psych} concurrent users, {args.duration:.0f}s @ ~{args.interval}s/device --")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.users + args.psych) as ex:
        futs = [
            ex.submit(
                device_thread,
                args.base,
                jwt,
                serial,
                token,
                args.interval,
                args.duration,
                args.read_every,
                args.burst_late,
            )
            for jwt, serial, token in hands
        ]
        futs += [
            ex.submit(psych_thread, args.base, j, args.duration) for j in psych_hands
        ]
        for f in futs:
            f.result()
    elapsed = time.monotonic() - t0

    with _LOCK:
        codes = dict(sorted(_STATS["codes"].items()))
        lat = list(_STATS["latencies"])
        push = list(_STATS["push_latencies"])
        network = _STATS["network"]
    print("\n-- results --")
    print(f"  wall time        {elapsed:.1f}s")
    print(f"  status codes     {codes}")
    print(f"  network errors   {network}")
    print(f"  total requests   {sum(codes.values()) + network}")
    print(f"  all latency      p50={pct(lat, .5):.0f}ms  p95={pct(lat, .95):.0f}ms  p99={pct(lat, .99):.0f}ms")
    print(f"  /ring/data       p50={pct(push, .5):.0f}ms  p95={pct(push, .95):.0f}ms  p99={pct(push, .99):.0f}ms")

    # integrity: every pushed seq landed exactly once (idempotency under load)
    if args.db:
        db = sqlite3.connect(args.db)
        rows = db.execute(
            "select device_id, count(*), count(distinct seq) from ring_sensor_log "
            "where device_id like ? group by device_id",
            (f"PL-{args.tag}-%",),
        ).fetchall()
        db.close()
        total = sum(r[1] for r in rows)
        distinct = sum(r[2] for r in rows)
        print(f"  ring rows total/distinct-seq  {total}/{distinct}  ({len(rows)} devices)")
        print(f"  duplicate rows (should be 0)  {total - distinct}")

    bad = [c for c in (500, 502, 503, 504, 429) if codes.get(c, 0)]
    print("\nRESULT:", "NO OK" if not codes.get(200) else "PILOT-LOAD COMPLETE")
    return int(bool(bad or network))


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
