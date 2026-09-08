"""Offline-outbox sync endpoints: batched journal + mood upsert + dedupe.

These mirror what the frontend outbox (src/api/outbox.ts) sends when a
patient journals while the clinic server is unreachable, then flushes when
it comes back.
"""

import uuid
from datetime import UTC, datetime


def _ts() -> str:
    return datetime.now(UTC).isoformat()


def test_offline_journal_sync_creates_and_dedupes(client, patient_user):
    entry = {
        "raw_content": f"offline note {uuid.uuid4().hex[:6]}",
        "timestamp": _ts(),
        "client_id": f"c-{uuid.uuid4().hex}",
    }
    auth = {"Authorization": f"Bearer {patient_user['access_token']}"}

    first = client.post("/api/sync/journals", json=[entry], headers=auth)
    assert first.status_code == 200
    body = first.json()
    assert body["synced"][0]["status"] == "created"
    assert body["synced"][0]["client_id"] == entry["client_id"]

    # Replay (outbox flush repeated / connection dropped after commit) must
    # not duplicate — the server returns duplicate and no second row lands.
    replay = client.post("/api/sync/journals", json=[entry], headers=auth)
    assert replay.status_code == 200
    assert replay.json()["synced"][0]["status"] == "duplicate"


def test_offline_mood_sync_creates_and_dedupes(client, patient_user):
    entry = {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "emoji": "😊",
        "label": "Calm",
        "timestamp": _ts(),
        "client_id": f"c-{uuid.uuid4().hex}",
    }
    auth = {"Authorization": f"Bearer {patient_user['access_token']}"}

    first = client.post("/api/sync/moods", json=[entry], headers=auth)
    assert first.status_code == 200
    assert first.json()["synced"][0]["status"] == "created"

    replay = client.post("/api/sync/moods", json=[entry], headers=auth)
    assert replay.status_code == 200
    assert replay.json()["synced"][0]["status"] == "duplicate"


def test_offline_sync_requires_auth(client):
    entry = {"raw_content": "no token", "timestamp": _ts(), "client_id": "c-x"}
    resp = client.post("/api/sync/journals", json=[entry])
    assert resp.status_code == 401 or resp.status_code == 403


def test_mixed_offline_batch_persists_both(client, patient_user):
    auth = {"Authorization": f"Bearer {patient_user['access_token']}"}
    j = {"raw_content": f"mixed {uuid.uuid4().hex[:6]}", "timestamp": _ts(), "client_id": "c-j1"}
    m = {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "emoji": "😌",
        "label": "Tired",
        "timestamp": _ts(),
        "client_id": "c-m1",
    }
    jr = client.post("/api/sync/journals", json=[j], headers=auth)
    mr = client.post("/api/sync/moods", json=[m], headers=auth)
    assert jr.status_code == 200 and jr.json()["count"] == 1
    assert mr.status_code == 200 and mr.json()["count"] == 1

    # Both are visible through the normal read APIs the journal/mood pages use.
    journals = client.get("/api/journal", headers=auth)
    assert journals.status_code == 200
    assert any(item["raw_content"] == j["raw_content"] for item in journals.json().get("items", []))

    moods = client.get("/api/mood", headers=auth)
    assert moods.status_code == 200
    assert any(item["emoji"] == m["emoji"] for item in moods.json())
