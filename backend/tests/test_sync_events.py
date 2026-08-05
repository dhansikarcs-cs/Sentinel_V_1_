import uuid

from app.services.event_store_service import event_store


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_event_store_append_and_filter(client):
    agg = f"agg_{uuid.uuid4().hex[:8]}"
    before = len(event_store.get_events(aggregate_id=agg))
    event_store.append("test:event", {"a": 1}, aggregate_type="test", aggregate_id=agg)
    events = event_store.get_events(aggregate_id=agg)
    assert len(events) == before + 1
    assert events[0].event_type == "test:event"
    filtered = event_store.get_events(event_type="test:event", aggregate_id=agg)
    assert all(e.event_type == "test:event" for e in filtered)


def test_event_store_replay_returns_count(client):
    agg = f"agg_{uuid.uuid4().hex[:8]}"
    before_events = event_store.replay()
    max_before = max((e.sequence for e in before_events), default=0)
    for _ in range(3):
        event_store.append("test:replay", {"n": 1}, aggregate_type="test", aggregate_id=agg)
    since = event_store.replay(from_sequence=max_before)
    assert len(since) == 3
    assert all(e.event_type == "test:replay" for e in since)


def test_journal_submission_writes_events(client, make_user):
    patient = make_user(role="patient")
    psych = make_user(role="psychologist")
    client.post(
        "/api/journal",
        json={"raw_content": "Everything feels calm and steady today."},
        headers=_auth(patient["access_token"]),
    )

    resp = client.get(f"/api/events/patient/{patient['username']}", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event_type"] == "journal:submitted" for e in events)


def test_events_api_requires_psychologist(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/events", headers=_auth(patient["access_token"]))
    assert resp.status_code == 403


def test_events_replay_endpoint(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/events/replay", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200
    assert "events_replayed" in resp.json()
