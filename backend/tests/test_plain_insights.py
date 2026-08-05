def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_patient(client, psych, patient):
    client.post(
        "/api/journal",
        headers=_auth(patient["access_token"]),
        json={"raw_content": "I feel calm and hopeful about this week. Things are steady."},
    )
    client.post(
        "/api/journal",
        headers=_auth(patient["access_token"]),
        json={"raw_content": "A little tired today but grateful for the small wins."},
    )
    client.post(
        "/api/followups",
        headers=_auth(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Breathing exercise", "description": ""},
    )


def test_plain_insights_structure_and_rule_fallback(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    _seed_patient(client, psych, patient)

    resp = client.get(f"/api/patients/{patient['username']}/plain-insights", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["source"] == "rule"
    assert isinstance(data["headline"], str) and data["headline"]
    assert isinstance(data["insights"], list) and len(data["insights"]) >= 3
    assert all(isinstance(i, str) and i for i in data["insights"])
    assert isinstance(data["suggestion"], str) and data["suggestion"]
    assert data["generated_at"]


def test_plain_insights_ai_when_model_available(client, make_user, monkeypatch):
    from app.services import plain_insights

    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    _seed_patient(client, psych, patient)

    def _fake_ollama(prompt, timeout=20, prompt_version=""):
        return '{"headline": "She is doing well this week.", "insights": ["Her mood is improving.", "She has been journaling regularly."], "suggestion": "Keep encouraging her."}'

    monkeypatch.setattr(plain_insights.ai_service, "_query_ollama", _fake_ollama)

    resp = client.get(f"/api/patients/{patient['username']}/plain-insights", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["source"] == "ai"
    assert data["provider"] == "ollama"
    assert data["headline"] == "She is doing well this week."
    assert data["suggestion"] == "Keep encouraging her."


def test_plain_insights_patient_can_see_own(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    _seed_patient(client, psych, patient)

    resp = client.get(f"/api/patients/{patient['username']}/plain-insights", headers=_auth(patient["access_token"]))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["headline"]


def test_plain_insights_denied_across_patients(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient")
    p2 = make_user(role="patient")
    _seed_patient(client, psych, p1)

    resp = client.get(f"/api/patients/{p1['username']}/plain-insights", headers=_auth(p2["access_token"]))
    assert resp.status_code == 403


def test_plain_insights_404_unknown_patient(client, make_user):
    psych = make_user(role="psychologist")
    resp = client.get("/api/patients/ghost_user/plain-insights", headers=_auth(psych["access_token"]))
    assert resp.status_code == 404
