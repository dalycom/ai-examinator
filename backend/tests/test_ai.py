from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def _clinical_setup(client: TestClient, headers: dict[str, str]) -> tuple[str, str, str]:
    clinic = client.post(
        "/api/v1/clinics",
        headers=headers,
        json={"name": "AI Clinic", "timezone": "UTC"},
    )
    assert clinic.status_code == 201
    clinic_id = clinic.json()["id"]

    patient = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "clinic_id": clinic_id,
            "given_name": "AI",
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


def _prepare_transcript(client: TestClient, headers: dict[str, str], session_id: str, patient_id: str) -> None:
    consent = client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"scopes": {"recording": True, "ai_processing": True}, "method": "verbal_confirmed"},
    )
    assert consent.status_code == 201

    recording = client.post(f"/api/v1/sessions/{session_id}/recording:start", headers=headers)
    assert recording.status_code == 200

    upload = client.post(
        f"/api/v1/sessions/{session_id}/audio:create-upload",
        headers=headers,
        json={"filename": "consultation.webm", "mime_type": "audio/webm"},
    )
    assert upload.status_code == 200

    finalized = client.post(
        f"/api/v1/sessions/{session_id}/audio:finalize",
        headers=headers,
        json={"size_bytes": 1024, "duration_ms": 11000},
    )
    assert finalized.status_code == 200


def test_ai_extraction_and_review(client: TestClient) -> None:
    tokens = register_org(client, slug=f"ai-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    assert session.status_code == 201
    session_id = session.json()["id"]

    blocked = client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)
    assert blocked.status_code == 403

    _prepare_transcript(client, headers, session_id, patient_id)

    no_consent = client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)
    assert no_consent.status_code == 200
    facts_payload = no_consent.json()
    assert facts_payload["run"]["status"] == "completed"
    assert len(facts_payload["facts"]) >= 2
    assert all(fact["is_ai_generated"] for fact in facts_payload["facts"])
    assert all(fact["provenance"]["model_id"] for fact in facts_payload["facts"])

    summary = client.get(f"/api/v1/sessions/{session_id}/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["is_ai_generated"] is True
    assert summary.json()["summary"]

    suggestions = client.get(f"/api/v1/sessions/{session_id}/suggestions", headers=headers)
    assert suggestions.status_code == 200
    items = suggestions.json()["suggestions"]
    assert len(items) >= 2
    assert any(item["suggestion_type"] == "red_flag" for item in items)

    suggestion_id = next(item["id"] for item in items if item["suggestion_type"] == "red_flag")
    decision = client.post(
        f"/api/v1/suggestions/{suggestion_id}/decision",
        headers=headers,
        json={"decision": "approved", "reason": "Clinically reasonable"},
    )
    assert decision.status_code == 200
    assert decision.json()["decision"]["status"] == "approved"

    provenance = client.get(f"/api/v1/suggestions/{suggestion_id}/provenance", headers=headers)
    assert provenance.status_code == 200
    assert provenance.json()["prompt_version"]

    editable = next(item for item in items if item["suggestion_type"] == "missing_question")
    edited = client.post(
        f"/api/v1/suggestions/{editable['id']}/decision",
        headers=headers,
        json={
            "decision": "edited",
            "edited_value": {"label": "Any visual aura or photophobia?"},
            "reason": "Clinician refined question",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["decision"]["status"] == "edited"
    assert "photophobia" in edited.json()["concept"]["label"]


def test_ai_async_extraction_execute(client: TestClient, db) -> None:
    from uuid import UUID

    from app.core.enums import Locale
    from app.core.tenant import Principal
    from app.modules.ai.service import AIService

    tokens = register_org(client, slug=f"ai-async-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]
    _prepare_transcript(client, headers, session_id, patient_id)

    me = client.get("/api/v1/auth/me", headers=headers)
    principal = Principal(
        user_id=UUID(me.json()["id"]),
        organization_id=UUID(me.json()["organization_id"]),
        permissions=frozenset({"ai:run", "ai:read", "ai:review", "governance:manage"}),
        locale=Locale.EN,
        email=me.json()["email"],
        full_name=me.json()["full_name"],
    )

    service = AIService(db)
    run = service.enqueue_extraction(principal, UUID(session_id))
    db.commit()
    assert run.status in {"completed", "pending"}

    if run.status == "pending":
        service.execute_extraction_run(run.id, principal)
        db.commit()

    facts = client.get(f"/api/v1/sessions/{session_id}/facts", headers=headers)
    assert facts.status_code == 200
    assert facts.json()["run"]["status"] == "completed"
    assert len(facts.json()["facts"]) >= 2


def test_ai_eval_harness() -> None:
    from app.modules.ai.eval import run_eval_suite, run_stub_eval
    from app.modules.ai.eval_dataset import case_count

    assert case_count() >= 50
    metrics = run_stub_eval()
    assert metrics.passed is True
    assert metrics.total_cases >= 50
    assert metrics.grounding_rate == 1.0
    assert metrics.red_flag_recall == 1.0

    subset = run_eval_suite()
    assert subset.passed is True
