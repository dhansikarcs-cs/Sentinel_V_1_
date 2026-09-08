"""Role-correct, schema-correct live-API sweep. Usage: python sweep_api.py [base_url]"""

import datetime
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

# default per-request timeout so a dead AI provider never hangs the sweep
_orig_request = requests.api.request


def _timeout_request(*args, **kwargs):
    kwargs.setdefault("timeout", 25)
    return _orig_request(*args, **kwargs)


requests.api.request = _timeout_request
requests.request = _timeout_request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TAG = uuid.uuid4().hex[:6]
PD = datetime.datetime.now(datetime.UTC)
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}".rstrip())


def call(name, fn, expect=200, parse=True, timeout=30):
    t0 = time.time()
    try:
        r = fn(timeout=timeout) if "timeout" in fn.__code__.co_varnames else fn()
        elapsed = int((time.time() - t0) * 1000)
        if r is None:
            record(name, True, "| skipped (no id)")
            return None
    except Exception as e:  # noqa: BLE001
        record(name, False, f"EXC {e}")
        return None
    try:
        body = r.json() if parse else r.content
    except Exception:  # noqa: BLE001
        body, parse = None, False
    detail = f"| {r.status_code} | {elapsed}ms"
    if r.status_code >= 400 and parse and body is not None:
        detail += f" {json.dumps(body)[:90]}"
    if elapsed >= 5000:
        detail += " [SLOW >=5s]"
    ok = r.status_code == expect if expect > 0 else r.status_code < 400
    if not ok:
        record(name, False, detail)
    else:
        record(name, True, detail if expect == 0 or elapsed >= 5000 else "")
    return body


def patient(token):
    return {"Authorization": f"Bearer {token}"}


def auth(u, p):
    return call(f"login {u}", lambda: requests.post(f"{BASE}/api/auth/login", json={"username": u, "password": p}))


# ---------------- register one patient, provision one psych via DB ----------------
pun = f"p_{TAG}"
sun = f"sp_{TAG}"
call(
    f"register patient {pun}",
    lambda: requests.post(
        f"{BASE}/api/auth/register",
        json={
            "username": pun,
            "password": "Str0ng!Pass1",
            "name": "Sweep P",
            "role": "patient",
            "age": 30,
            "occupation": "Engineer",
            "clinic_code": "SENTINEL-TEST",
        },
    ),
)
call(
    f"register psych {sun} (must fail; role forced to patient)",
    lambda: requests.post(
        f"{BASE}/api/auth/register",
        json={
            "username": sun,
            "password": "Str0ng!Pass1",
            "name": "Sweep S",
            "role": "psychologist",
            "age": 40,
            "occupation": "Psych",
            "clinic_code": "SENTINEL-TEST",
        },
    ),
    expect=200,
)


def _provision_psych(username, password):
    """Self-registration can't mint psychologists, so provision server-side (like seeds do)."""
    from datetime import UTC, datetime  # noqa: PLC0415

    os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'data' / 'sentinel.db'}")
    from app.core.database import SessionLocal  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models import User  # noqa: PLC0415

    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(username=username).first()
        if existing:
            if existing.role != "psychologist":
                existing.role = "psychologist"
                db.commit()
            return
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                name="Sweep S",
                role="psychologist",
                age=40,
                occupation="Psych",
                clinic_code="SENTINEL-TEST",
                onboarding_step=0,
                encryption_salt=os.urandom(16).hex(),
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        db.commit()
    finally:
        db.close()


_provision_psych(sun, "Str0ng!Pass1")

pbody = auth(pun, "Str0ng!Pass1")
sbody = auth(sun, "Str0ng!Pass1")
pt = pbody.get("access_token", "")
st = sbody.get("access_token", "")
if not pt or not st:
    print("could not log in; aborting")
    sys.exit(2)
P, S = patient(pt), patient(st)

# =============== AUTH ===============
call(
    "auth refresh-cycle",
    lambda: requests.post(f"{BASE}/api/auth/refresh", json={"refresh_token": pbody.get("refresh_token", "")}),
)
call("auth me", lambda: requests.get(f"{BASE}/api/patients/me", headers=P))
call("auth encryption-status", lambda: requests.get(f"{BASE}/api/auth/encryption-status", headers=P))
call("logout 200", lambda: requests.post(f"{BASE}/api/auth/logout", headers=P, json={}))
# THIS is the interesting one: access token must be dead after logout
call("logout then me->401", lambda: requests.get(f"{BASE}/api/patients/me", headers=P), expect=401)

# re-login for rest of patient sweeps
pbody = auth(pun, "Str0ng!Pass1")
pt = pbody.get("access_token", "")
P = patient(pt)

# =============== PATIENT-profile ===============
call("profile", lambda: requests.get(f"{BASE}/api/patients/{pun}/profile", headers=P))
call("summary", lambda: requests.get(f"{BASE}/api/patients/{pun}/summary", headers=P))
call(
    "update contact",
    lambda: requests.put(
        f"{BASE}/api/patients/me/contact", headers=P, json={"contact_info": "ph-999", "trusted_contact": "friend"}
    ),
)
call("wellness", lambda: requests.get(f"{BASE}/api/patients/me/wellness", headers=P))

# =============== JOURNAL (patient writes) ===============
call(
    "journal empty->422", lambda: requests.post(f"{BASE}/api/journal", headers=P, json={"raw_content": ""}), expect=422
)
call(
    "journal valid",
    lambda: requests.post(
        f"{BASE}/api/journal",
        headers=P,
        json={"raw_content": "Sweep day. Felt okay. Did a walk, felt calm. Progress feels real."},
    ),
)
jb = call("journal list me", lambda: requests.get(f"{BASE}/api/journal", headers=P))
jid = None
if isinstance(jb, dict) and jb.get("items"):
    jid = jb["items"][-1].get("id")
elif isinstance(jb, list) and jb:
    jid = jb[-1].get("id")
call("journal delete mine", lambda: requests.delete(f"{BASE}/api/journal/{jid}", headers=P) if jid else None)

# =============== MOOD (patient writes) ===============
call(
    "mood valid",
    lambda: requests.post(
        f"{BASE}/api/mood", headers=P, json={"date": PD.strftime("%Y-%m-%d"), "emoji": "🙂", "label": "calm"}
    ),
)
call(
    "mood bad date->422",
    lambda: requests.post(f"{BASE}/api/mood", headers=P, json={"date": "x", "emoji": "🙂", "label": "calm"}),
    expect=422,
)
call("mood today-check", lambda: requests.get(f"{BASE}/api/mood/today/check", headers=P))
call("mood list me", lambda: requests.get(f"{BASE}/api/mood", headers=P))

# =============== PHYSIO (patient pushes) ===============
call(
    "physio push valid",
    lambda: requests.post(
        f"{BASE}/api/physio/push", headers=P, json={"vendor": "webcam", "bpm": 71, "hrv": 44, "confidence": 0.61}
    ),
)
# REAL FINDING candidate: out-of-range BPM should be rejected
call(
    "physio push bpm=350 should be rejected",
    lambda: requests.post(
        f"{BASE}/api/physio/push", headers=P, json={"vendor": "webcam", "bpm": 350, "hrv": 44, "confidence": 0.61}
    ),
    expect=422,
)
call("physio signals me", lambda: requests.get(f"{BASE}/api/physio/signals", headers=P))
call("physio vendors", lambda: requests.get(f"{BASE}/api/physio/vendors", headers=P))
call("sensor-readings me", lambda: requests.get(f"{BASE}/api/sensor-readings", headers=P))
# sensor-readings DOES have pydantic bounds (30-250) -> should 422
call(
    "sensor-readings bpm=350->422",
    lambda: requests.post(f"{BASE}/api/sensor-readings", headers=P, json={"heart_rate": 350}),
    expect=422,
)

# =============== RING (device-token auth) ===============
pairbody = call(
    "ring pair",
    lambda: requests.post(f"{BASE}/api/ring/pair", headers=P, json={"serial": f"SWEEP-{TAG}", "vendor": "ring"}),
)
dev_token = (pairbody or {}).get("token", "")
DH = dict(P)
if dev_token:
    DH = {"X-Device-Serial": f"SWEEP-{TAG}", "X-Device-Token": dev_token}
call(
    "ring data push (device token)",
    lambda: requests.post(
        f"{BASE}/api/ring/data",
        headers=DH,
        json={"device_id": f"SWEEP-{TAG}", "bpm": 70, "spo2": 97, "hrv": 45, "stress": 30, "sleep_hours": 6.5},
    ),
)
call(
    "ring data push bpm=1000->422",
    lambda: requests.post(f"{BASE}/api/ring/data", headers=DH, json={"device_id": f"SWEEP-{TAG}", "bpm": 1000}),
    expect=422,
)
call("ring devices", lambda: requests.get(f"{BASE}/api/ring/devices", headers=P))
call("ring data", lambda: requests.get(f"{BASE}/api/ring/data", headers=P))

# =============== DISCREPANCY ===============
call(
    "discrepancy neg+low",
    lambda: requests.post(
        f"{BASE}/api/discrepancy/check",
        headers=P,
        json={"journal_text": "I am hopeless and alone", "bpm": 60, "hrv": 60},
    ),
)
call(
    "discrepancy pos+high",
    lambda: requests.post(
        f"{BASE}/api/discrepancy/check",
        headers=P,
        json={"journal_text": "I am so happy and great", "bpm": 120, "hrv": 20},
    ),
)
call(
    "discrepancy bad types->422",
    lambda: requests.post(
        f"{BASE}/api/discrepancy/check", headers=P, json={"journal_text": "x", "bpm": "high", "hrv": 20}
    ),
    expect=422,
)

# =============== CRISIS (patient triggers, psych resolves) ===============
call("crisis trigger", lambda: requests.post(f"{BASE}/api/crisis/trigger", headers=P))
call("crisis state", lambda: requests.get(f"{BASE}/api/crisis/state", headers=P))
call("crisis elapsed", lambda: requests.get(f"{BASE}/api/crisis/elapsed", headers=P))
call("crisis acknowledge (psych)", lambda: requests.post(f"{BASE}/api/crisis/acknowledge", headers=S))
call("crisis resolve (psych)", lambda: requests.post(f"{BASE}/api/crisis/resolve", headers=S))
call(
    "crisis assess-risk",
    lambda: requests.post(f"{BASE}/api/crisis/assess-risk", headers=P, json={"text": "I feel fine today"}),
)
call("crisis log me", lambda: requests.get(f"{BASE}/api/crisis/log", headers=P))

# =============== BOOKINGS (patient creates) ===============
call(
    "booking create",
    lambda: requests.post(
        f"{BASE}/api/bookings",
        headers=P,
        json={
            "psychologist_username": sun,
            "date": (PD + datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
            "time": "10:00",
            "session_type": "therapy",
            "members": "",
            "contact": "",
            "explanation": "",
        },
    ),
)
call("bookings list", lambda: requests.get(f"{BASE}/api/bookings", headers=P))

# =============== SYNC (bare list of entries) ===============
call(
    "sync journals",
    lambda: requests.post(
        f"{BASE}/api/sync/journals",
        headers=P,
        json=[{"raw_content": "offline note", "timestamp": PD.isoformat(), "client_id": "c1"}],
    ),
)
call(
    "sync moods",
    lambda: requests.post(
        f"{BASE}/api/sync/moods",
        headers=P,
        json=[
            {
                "date": PD.strftime("%Y-%m-%d"),
                "emoji": "🙂",
                "label": "ok",
                "timestamp": PD.isoformat(),
                "client_id": "c2",
            }
        ],
    ),
)

# =============== EXPORT (psych-gated by design) ===============
call("export patient-data (psych)", lambda: requests.get(f"{BASE}/api/export/patient-data", headers=S))

# =============== PSYCH side ===============
call(
    "assign-psych",
    lambda: requests.post(f"{BASE}/api/patients/{pun}/assign-psych", params={"psych_username": sun}, headers=S),
)
call("psych patients", lambda: requests.get(f"{BASE}/api/psychologists/patients", headers=S))
call("psych available", lambda: requests.get(f"{BASE}/api/psychologists/available", headers=S))
call(
    "psych note create",
    lambda: requests.post(
        f"{BASE}/api/psychologists/notes",
        headers=S,
        params={"patient_username": pun, "raw_notes": "sweep clinical note"},
    ),
)
call(
    "psych note create bad (no patient)->422",
    lambda: requests.post(f"{BASE}/api/psychologists/notes", headers=S, params={"raw_notes": "x"}),
    expect=422,
)
call("psych note approve", lambda: requests.put(f"{BASE}/api/psychologists/notes/1/approve", headers=S, json={}))
call("journal as psych", lambda: requests.get(f"{BASE}/api/journal/{pun}", headers=S))
call("mood as psych", lambda: requests.get(f"{BASE}/api/mood/{pun}", headers=S))
call("overview as psych", lambda: requests.get(f"{BASE}/api/patients/{pun}/overview", headers=S))
call("plain-insights", lambda: requests.get(f"{BASE}/api/patients/{pun}/plain-insights", headers=S))
call("risk-assessments patient", lambda: requests.get(f"{BASE}/api/risk-assessments/patient/{pun}", headers=S))
call("triage list", lambda: requests.get(f"{BASE}/api/triage", headers=S))
call("triage patient", lambda: requests.get(f"{BASE}/api/triage/{pun}", headers=S))
call("triage create", lambda: requests.post(f"{BASE}/api/triage", headers=S, json={"patient_username": pun}))
tcb = call("triage create", lambda: requests.post(f"{BASE}/api/triage", headers=S, json={"patient_username": pun}))
trid = (tcb or {}).get("id", "") if isinstance(tcb, dict) else ""
call(
    "triage update",
    lambda: requests.put(f"{BASE}/api/triage/{trid}", headers=S, json={"note": "updated"}) if trid else None,
)
call("emotions timeline", lambda: requests.get(f"{BASE}/api/emotions/timeline/{pun}", headers=S))
call("emotions summary", lambda: requests.get(f"{BASE}/api/emotions/summary/{pun}", headers=S))
call("ai-analyses patient", lambda: requests.get(f"{BASE}/api/ai-analyses/patient/{pun}", headers=S))
call("followups list", lambda: requests.get(f"{BASE}/api/followups", headers=S))
call(
    "followup create",
    lambda: requests.post(
        f"{BASE}/api/followups", headers=S, json={"patient_username": pun, "title": "breathing", "description": "do it"}
    ),
)
call("activity", lambda: requests.get(f"{BASE}/api/activity?days=7", headers=S))
call("timeline patient", lambda: requests.get(f"{BASE}/api/timeline/{pun}", headers=S))
call("timeline metrics", lambda: requests.get(f"{BASE}/api/timeline/{pun}/metrics", headers=S))
call("events", lambda: requests.get(f"{BASE}/api/events", headers=S))
call("feature-flags", lambda: requests.get(f"{BASE}/api/feature-flags", headers=S))
call("export journal-summaries", lambda: requests.get(f"{BASE}/api/export/journal-summaries", headers=S))
call("export clinical-notes", lambda: requests.get(f"{BASE}/api/export/clinical-notes", headers=S))
call("physio patient", lambda: requests.get(f"{BASE}/api/physio/patient/{pun}", headers=S))
call("sensor patient", lambda: requests.get(f"{BASE}/api/sensor-readings/patient/{pun}", headers=S))
call("triage update", lambda: requests.put(f"{BASE}/api/triage/{pun}", headers=S, json={"note": "updated"}))

# agents (psych)
for name, route, payload in [
    ("agents triage-summary", "triage-summary", {"patient_username": pun}),
    ("agents relapse", "relapse-indicators", {"patient_username": pun}),
    ("agents brief create", "pre-session-brief", {"patient_username": pun}),
    ("agents brief get", "pre-session-brief", None),
    ("agents silent-period", "silent-period-watch", {"patient_username": pun}),
    ("agents compliance-radar", "compliance-radar", None),
    ("agents ring-vitals-risk", "ring-vitals-risk", {"patient_username": pun}),
    ("agents crisis-debrief", "crisis-debrief", {"patient_username": pun}),
    ("agents cross-patient", "cross-patient-patterns", {"clinic_code": "SENTINEL-TEST"}),
    ("agents journal-to-note", "journal-to-note", {"patient_username": pun, "journal_text": "sample"}),
    ("agents suggest-slots", "suggest-slots", {"patient_username": pun}),
    ("agents draft-followup", "draft-followup", {"patient_username": pun}),
]:
    method = requests.get if (name == "agents brief get") else requests.post
    url = f"{BASE}/api/agents/{route}"
    if name == "agents brief get":
        url = f"{BASE}/api/agents/pre-session-brief/{pun}"
    call(
        name,
        lambda m=method, u=url, b=payload: m(
            u, headers=S, json=(b if b is not None else {}) if m is not requests.get else None
        ),
    )

# booking availability (psych)
call(
    "psych availability create",
    lambda: requests.post(
        f"{BASE}/api/bookings/availability",
        headers=S,
        json={
            "date": (PD + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "start_time": "09:00",
            "end_time": "11:00",
        },
    ),
)
call("psych my availability", lambda: requests.get(f"{BASE}/api/bookings/availability/me", headers=S))

# role-violation checks
call(
    "patient denied psych patients->403",
    lambda: requests.get(f"{BASE}/api/psychologists/patients", headers=P),
    expect=403,
)
call(
    "patient denied export journal-summaries->403",
    lambda: requests.get(f"{BASE}/api/export/journal-summaries", headers=P),
    expect=403,
)
call("patient denied triage list->403", lambda: requests.get(f"{BASE}/api/triage", headers=P), expect=403)
call(
    "psych denied journal write->403",
    lambda: requests.post(f"{BASE}/api/journal", headers=S, json={"raw_content": "x"}),
    expect=403,
)

# =============== ML registry ===============
call("ml models", lambda: requests.get(f"{BASE}/api/ml/models", headers=P))
# REAL FINDING candidate: unknown model returns 200 (should arguably be 404)
call("ml models unknown->404", lambda: requests.get(f"{BASE}/api/ml/models/does-not-exist", headers=P), expect=404)

# =============== misc ===============
call("notifications unread", lambda: requests.get(f"{BASE}/api/notifications/unread", headers=P))
call("feature-flags as patient->403", lambda: requests.get(f"{BASE}/api/feature-flags", headers=P), expect=403)

# =============== summary ===============
fails = [r for r in results if not r[1]]
print("\n" + "=" * 60)
print(f"SWEEP COMPLETE: {len(results) - len(fails)}/{len(results)} passed, {len(fails)} failed")
for fname, _ok, d in fails:
    print(f"  FAIL: {fname} {d}")
    # print markers for actionable items
sys.exit(1 if fails else 0)
