from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def _setup_patient(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    clinic = client.post(
        "/api/v1/clinics",
        headers=headers,
        json={"name": "Phase5 Clinic", "timezone": "UTC"},
    )
    assert clinic.status_code == 201
    clinic_id = clinic.json()["id"]

    patient = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "clinic_id": clinic_id,
            "given_name": "Phase",
            "family_name": "Five",
            "preferred_locale": "en",
        },
    )
    assert patient.status_code == 201
    return patient.json()["id"], clinic_id


def test_lab_imaging_and_fhir(client: TestClient) -> None:
    tokens = register_org(client, slug=f"p5-lab-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, _ = _setup_patient(client, headers)

    created = client.post(
        f"/api/v1/patients/{patient_id}/lab-imaging-results",
        headers=headers,
        json={
            "result_type": "lab",
            "loinc_code": "718-7",
            "code_display": "Hemoglobin",
            "value": "13.2",
            "unit": "g/dL",
        },
    )
    assert created.status_code == 201
    assert created.json()["code_display"] == "Hemoglobin"

    listed = client.get(f"/api/v1/patients/{patient_id}/lab-imaging-results", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fhir_patient = client.get(f"/api/v1/fhir/Patient/{patient_id}", headers=headers)
    assert fhir_patient.status_code == 200
    body = fhir_patient.json()
    assert body["resourceType"] == "Patient"
    assert body["identifier"][0]["value"].startswith("MRN-")

    observations = client.get(f"/api/v1/fhir/Observation?patient={patient_id}", headers=headers)
    assert observations.status_code == 200
    assert observations.json()["resourceType"] == "Bundle"
    assert observations.json()["total"] >= 1


def test_dashboard_and_report(client: TestClient) -> None:
    tokens = register_org(client, slug=f"p5-dash-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, _ = _setup_patient(client, headers)

    dashboard = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dashboard.status_code == 200
    summary = dashboard.json()
    assert summary["patients_total"] >= 1
    assert "pending_ai_reviews" in summary

    report = client.post(
        "/api/v1/reports",
        headers=headers,
        json={"patient_id": patient_id, "locale": "ar", "format": "html"},
    )
    assert report.status_code == 201
    report_id = report.json()["id"]
    assert report.json()["locale"] == "ar"
    assert 'dir="rtl"' in report.json()["body_html"]

    fetched = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"]


def test_export_erasure_and_notifications(client: TestClient) -> None:
    tokens = register_org(client, slug=f"p5-export-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, _ = _setup_patient(client, headers)

    export = client.post(
        "/api/v1/export-jobs",
        headers=headers,
        json={"patient_id": patient_id, "scope": "patient"},
    )
    assert export.status_code == 201
    job_id = export.json()["id"]
    assert export.json()["status"] == "completed"

    download = client.get(f"/api/v1/export-jobs/{job_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.json()["scope"] == "patient"
    assert download.json()["fhir_patient"]["resourceType"] == "Patient"

    notifications = client.get("/api/v1/notifications", headers=headers)
    assert notifications.status_code == 200
    assert len(notifications.json()) >= 1
    notification_id = notifications.json()[0]["id"]
    read = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    erasure = client.post(
        "/api/v1/erasure-requests",
        headers=headers,
        json={"patient_id": patient_id, "reason": "Patient DSAR erasure request"},
    )
    assert erasure.status_code == 201
    request_id = erasure.json()["id"]

    reviewed = client.post(
        f"/api/v1/erasure-requests/{request_id}/review",
        headers=headers,
        json={"decision": "approved", "reason": "Valid DSAR"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"

    completed = client.post(f"/api/v1/erasure-requests/{request_id}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    patient = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert patient.status_code == 404


def test_governance_dashboard_and_retention(client: TestClient) -> None:
    tokens = register_org(client, slug=f"p5-gov-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])

    dashboard = client.get("/api/v1/governance/dashboard", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert len(body["feature_flags"]) >= 1
    assert "retention_policies" in body

    policies = client.get("/api/v1/retention-policies", headers=headers)
    assert policies.status_code == 200
    assert any(row["resource_type"] == "patient" for row in policies.json())

    updated = client.put(
        "/api/v1/retention-policies/patient",
        headers=headers,
        json={"retention_days": 4000, "erasure_enabled": True},
    )
    assert updated.status_code == 200
    assert updated.json()["retention_days"] == 4000


def test_dashboard_overview(client: TestClient) -> None:
    tokens = register_org(client, slug=f"p5-overview-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])

    overview = client.get("/api/v1/dashboard/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert "summary" in body
    assert "recent_patients" in body
    assert "ai_status" in body
    assert body["ai_status"]["eval_passed"] is True
