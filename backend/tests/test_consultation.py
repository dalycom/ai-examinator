from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def _clinical_setup(client: TestClient, headers: dict[str, str]) -> tuple[str, str, str]:
    clinic = client.post(
        "/api/v1/clinics",
        headers=headers,
        json={"name": "Consult Clinic", "timezone": "UTC"},
    )
    assert clinic.status_code == 201
    clinic_id = clinic.json()["id"]

    patient = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "clinic_id": clinic_id,
            "given_name": "Consult",
            "family_name": "Patient",
            "preferred_locale": "en",
        },
    )
    assert patient.status_code == 201
    patient_id = patient.json()["id"]

    me = client.get("/api/v1/auth/me", headers=headers)
    clinician_id = me.json()["id"]

    encounter = client.post(
        "/api/v1/encounters",
        headers=headers,
        json={
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "clinician_id": clinician_id,
        },
    )
    assert encounter.status_code == 201
    return patient_id, encounter.json()["id"], clinic_id


def test_consultation_workflow(client: TestClient) -> None:
    tokens = register_org(client, slug=f"consult-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    consent = client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={
            "scopes": {"recording": True, "ai_processing": True},
            "method": "verbal_confirmed",
            "encounter_id": encounter_id,
        },
    )
    assert consent.status_code == 201

    blocked = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    assert blocked.status_code == 201
    session_id = blocked.json()["id"]

    no_consent_patient = client.post(
        "/api/v1/patients",
        headers=headers,
        json={"given_name": "No", "family_name": "Consent", "preferred_locale": "en"},
    )
    no_consent_id = no_consent_patient.json()["id"]
    me = client.get("/api/v1/auth/me", headers=headers)
    no_encounter = client.post(
        "/api/v1/encounters",
        headers=headers,
        json={
            "patient_id": no_consent_id,
            "clinic_id": client.get("/api/v1/clinics", headers=headers).json()[0]["id"],
            "clinician_id": me.json()["id"],
        },
    )
    no_session = client.post(
        f"/api/v1/encounters/{no_encounter.json()['id']}/sessions",
        headers=headers,
        json={},
    )
    assert no_session.status_code == 201
    denied = client.post(
        f"/api/v1/sessions/{no_session.json()['id']}/recording:start",
        headers=headers,
    )
    assert denied.status_code == 403

    recording = client.post(f"/api/v1/sessions/{session_id}/recording:start", headers=headers)
    assert recording.status_code == 200
    assert recording.json()["status"] == "recording"

    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio:create-upload",
        headers=headers,
        json={"filename": "consultation.webm", "mime_type": "audio/webm"},
    )
    assert upload.status_code == 200
    assert upload.json()["upload_url"]

    finalized = client.post(
        f"/api/v1/sessions/{session_id}/audio:finalize",
        headers=headers,
        json={"size_bytes": 1024, "duration_ms": 11000},
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "transcribed"

    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript", headers=headers)
    assert transcript.status_code == 200
    segments = transcript.json()
    assert len(segments) >= 2

    segment_id = segments[0]["id"]
    corrected = client.patch(
        f"/api/v1/sessions/{session_id}/transcript/{segment_id}",
        headers=headers,
        json={"corrected_text": "Good morning. What brings you in today? (corrected)"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["is_corrected"] is True

    note = client.get(f"/api/v1/sessions/{session_id}/note", headers=headers)
    assert note.status_code == 200
    assert note.json()["status"] == "draft"

    updated = client.patch(
        f"/api/v1/sessions/{session_id}/note",
        headers=headers,
        json={
            "content": {
                "subjective": "Headache for two days.",
                "objective": "Alert, no fever.",
                "assessment": "Tension headache likely.",
                "plan": "Hydration, follow up if worsening.",
            }
        },
    )
    assert updated.status_code == 200

    signed = client.post(f"/api/v1/sessions/{session_id}/note:sign", headers=headers)
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"
    assert signed.json()["content_hash"]

    session = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert session.json()["status"] == "completed"

    addendum = client.post(
        f"/api/v1/sessions/{session_id}/note:addendum",
        headers=headers,
        json={"content": {"subjective": "", "objective": "", "assessment": "Addendum", "plan": ""}},
    )
    assert addendum.status_code == 201
    assert addendum.json()["status"] == "draft"
    assert addendum.json()["addendum_of_id"] == signed.json()["id"]
