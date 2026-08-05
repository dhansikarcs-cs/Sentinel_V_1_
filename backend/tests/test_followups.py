def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_create_followup_with_due_date_roundtrip(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    resp = client.post(
        "/api/followups",
        headers=auth_headers(psych["access_token"]),
        json={
            "patient_username": patient["username"],
            "title": "Breathing exercise",
            "description": "10 slow breaths, twice daily",
            "due_date": "2026-08-12",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["due_date"] == "2026-08-12"
    assert data["psychologist_username"] == psych["username"]
    assert data["patient_username"] == patient["username"]


def test_create_followup_without_due_date_defaults_empty(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    resp = client.post(
        "/api/followups",
        headers=auth_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Journal", "description": ""},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["due_date"] == ""


def test_patient_sees_only_own_followups(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient")
    p2 = make_user(role="patient")
    for pat in (p1, p2):
        client.post(
            "/api/followups",
            headers=auth_headers(psych["access_token"]),
            json={"patient_username": pat["username"], "title": f"Task for {pat['username']}", "description": ""},
        )
    resp = client.get("/api/followups", headers=auth_headers(p1["access_token"]))
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert f"Task for {p1['username']}" in titles
    assert f"Task for {p2['username']}" not in titles


def test_grade_and_regrade_by_psychologist(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    created = client.post(
        "/api/followups",
        headers=auth_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Mindfulness", "description": ""},
    ).json()
    task_id = created["id"]

    first = client.put(
        f"/api/followups/{task_id}",
        headers=auth_headers(patient["access_token"]),
        json={"status": "completed", "grade": "none"},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    graded = client.put(
        f"/api/followups/{task_id}",
        headers=auth_headers(psych["access_token"]),
        json={"status": "completed", "grade": "green"},
    )
    assert graded.status_code == 200, graded.text
    assert graded.json()["grade"] == "green"
    assert graded.json()["approved_by"] == psych["username"]

    regraded = client.put(
        f"/api/followups/{task_id}",
        headers=auth_headers(psych["access_token"]),
        json={"status": "completed", "grade": "yellow"},
    )
    assert regraded.status_code == 200
    assert regraded.json()["grade"] == "yellow"


def test_patient_cannot_grade_own_task(client, make_user):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient")
    created = client.post(
        "/api/followups",
        headers=auth_headers(psych["access_token"]),
        json={"patient_username": patient["username"], "title": "Task", "description": ""},
    ).json()
    resp = client.put(
        f"/api/followups/{created['id']}",
        headers=auth_headers(patient["access_token"]),
        json={"status": "completed", "grade": "green"},
    )
    assert resp.status_code == 200
    assert resp.json()["grade"] == ""


def test_patient_cannot_touch_another_patients_task(client, make_user):
    psych = make_user(role="psychologist")
    p1 = make_user(role="patient")
    p2 = make_user(role="patient")
    created = client.post(
        "/api/followups",
        headers=auth_headers(psych["access_token"]),
        json={"patient_username": p1["username"], "title": "Private task", "description": ""},
    ).json()
    resp = client.put(
        f"/api/followups/{created['id']}",
        headers=auth_headers(p2["access_token"]),
        json={"status": "completed", "grade": "none"},
    )
    assert resp.status_code == 404
