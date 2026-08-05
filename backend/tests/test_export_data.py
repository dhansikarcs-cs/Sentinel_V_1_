import csv
import io

from app.models.user import User


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_text() -> str:
    return "A calm day with hopeful thoughts about the future."


def test_psychologist_exports_assigned_patient_journals(client, make_user, db_session):
    psych = make_user(role="psychologist")
    patient = make_user(role="patient", assigned_psych=psych["username"])
    row = db_session.query(User).filter(User.username == patient["username"]).first()
    row.assigned_psych = psych["username"]
    db_session.commit()

    client.post("/api/journal", json={"raw_content": _make_text()}, headers=_auth(patient["access_token"]))

    resp = client.get("/api/export/journal-summaries", headers=_auth(psych["access_token"]))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    assert rows[0][0] == "Patient"
    assert any(r[0] == patient["username"] for r in rows[1:])


def test_export_requires_psychologist(client, make_user):
    patient = make_user(role="patient")
    resp = client.get("/api/export/journal-summaries", headers=_auth(patient["access_token"]))
    assert resp.status_code == 403


def test_export_requires_auth(client):
    resp = client.get("/api/export/journal-summaries")
    assert resp.status_code == 401


def test_export_rejects_invalid_days(client, make_user):
    psych = make_user(role="psychologist")
    for bad in (0, 366):
        resp = client.get(f"/api/export/journal-summaries?days={bad}", headers=_auth(psych["access_token"]))
        assert resp.status_code == 422


def test_export_scopes_to_assigned_patients(client, make_user, db_session):
    psych = make_user(role="psychologist")
    other_psych = make_user(role="psychologist")
    assigned = make_user(role="patient")
    unassigned = make_user(role="patient")

    row = db_session.query(User).filter(User.username == assigned["username"]).first()
    row.assigned_psych = psych["username"]
    db_session.commit()

    client.post("/api/journal", json={"raw_content": _make_text()}, headers=_auth(assigned["access_token"]))
    client.post("/api/journal", json={"raw_content": _make_text()}, headers=_auth(unassigned["access_token"]))

    resp = client.get("/api/export/journal-summaries", headers=_auth(psych["access_token"]))
    rows = list(csv.reader(io.StringIO(resp.text)))
    patients_in_export = {r[0] for r in rows[1:] if r}
    assert assigned["username"] in patients_in_export
    assert unassigned["username"] not in patients_in_export

    resp_other = client.get("/api/export/journal-summaries", headers=_auth(other_psych["access_token"]))
    other_patients = {r[0] for r in list(csv.reader(io.StringIO(resp_other.text)))[1:] if r}
    assert assigned["username"] not in other_patients
