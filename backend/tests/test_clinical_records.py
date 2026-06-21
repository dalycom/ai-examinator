from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def test_patient_crud_and_timeline(client: TestClient) -> None:
    tokens = register_org(client, slug=f"clinical-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])

    clinic = client.post(
        "/api/v1/clinics",
        headers=headers,
        json={"name": "Clinical Clinic", "timezone": "UTC"},
    )
    assert clinic.status_code == 201
    clinic_id = clinic.json()["id"]

    create_patient = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "clinic_id": clinic_id,
            "given_name": "Synthetic",
            "family_name": "Patient",
            "date_of_birth": "1988-04-12",
            "sex": "female",
            "preferred_locale": "ar",
        },
    )
    assert create_patient.status_code == 201
    patient = create_patient.json()
    patient_id = patient["id"]
    assert patient["mrn"].startswith("MRN-")

    allergy = client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"substance_name": "Penicillin", "reaction": "Rash", "severity": "moderate"},
    )
    assert allergy.status_code == 201

    history = client.post(
        f"/api/v1/patients/{patient_id}/history",
        headers=headers,
        json={"category": "medical", "description": "Hypertension"},
    )
    assert history.status_code == 201

    me = client.get("/api/v1/auth/me", headers=headers)
    clinician_id = me.json()["id"]
    starts = datetime.now(UTC) + timedelta(hours=1)
    ends = starts + timedelta(minutes=30)

    appointment = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "clinician_id": clinician_id,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
        },
    )
    assert appointment.status_code == 201

    encounter = client.post(
        "/api/v1/encounters",
        headers=headers,
        json={
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "clinician_id": clinician_id,
            "appointment_id": appointment.json()["id"],
        },
    )
    assert encounter.status_code == 201

    timeline = client.get(f"/api/v1/patients/{patient_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()) >= 3

    icd10 = client.get("/api/v1/terminology/icd10?q=headache", headers=headers)
    assert icd10.status_code == 200
    assert any(item["code"] == "R51" for item in icd10.json())
