"""Automated HITL workflow validation (Phase 3 engineering gates)."""

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_ai import _clinical_setup, _prepare_transcript
from tests.test_auth import auth_headers, register_org


def test_hitl_s1_ai_outputs_labeled(client: TestClient) -> None:
    """S1 — AI outputs always labeled as suggestions."""
    tokens = register_org(client, slug=f"hitl-s1-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]
    _prepare_transcript(client, headers, session_id, patient_id)

    extract = client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)
    assert extract.status_code == 200

    facts = client.get(f"/api/v1/sessions/{session_id}/facts", headers=headers).json()["facts"]
    suggestions = client.get(f"/api/v1/sessions/{session_id}/suggestions", headers=headers).json()["suggestions"]
    summary = client.get(f"/api/v1/sessions/{session_id}/summary", headers=headers).json()

    assert facts and all(item["is_ai_generated"] for item in facts)
    assert suggestions and all(item["is_ai_generated"] for item in suggestions)
    assert summary["is_ai_generated"] is True


def test_hitl_s2_red_flags_reviewable(client: TestClient) -> None:
    """S2 — Red-flag suggestions visible and reviewable."""
    tokens = register_org(client, slug=f"hitl-s2-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]
    _prepare_transcript(client, headers, session_id, patient_id)
    client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)

    suggestions = client.get(f"/api/v1/sessions/{session_id}/suggestions", headers=headers).json()["suggestions"]
    red_flags = [item for item in suggestions if item["suggestion_type"] == "red_flag"]
    assert red_flags
    assert all(item["decision"]["status"] == "pending" for item in red_flags)


def test_hitl_s5_no_auto_sign_from_ai(client: TestClient) -> None:
    """S5 — AI extraction must not auto-sign; clinician must explicitly sign."""
    tokens = register_org(client, slug=f"hitl-s5-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]
    _prepare_transcript(client, headers, session_id, patient_id)
    client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)

    note_after_extract = client.get(f"/api/v1/sessions/{session_id}/note", headers=headers)
    assert note_after_extract.status_code == 200
    assert note_after_extract.json()["status"] == "draft"

    session_state = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert session_state.json()["status"] != "completed"

    signed = client.post(f"/api/v1/sessions/{session_id}/note:sign", headers=headers)
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"


def test_hitl_v4_v5_review_decisions_audited(client: TestClient) -> None:
    """V4/V5 — AI extraction with approve/reject/edit decisions."""
    tokens = register_org(client, slug=f"hitl-v45-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]
    _prepare_transcript(client, headers, session_id, patient_id)
    client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)

    suggestions = client.get(f"/api/v1/sessions/{session_id}/suggestions", headers=headers).json()["suggestions"]
    target = next(item for item in suggestions if item["suggestion_type"] != "red_flag")

    rejected = client.post(
        f"/api/v1/suggestions/{target['id']}/decision",
        headers=headers,
        json={"decision": "rejected", "reason": "Not clinically indicated in this context"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["decision"]["status"] == "rejected"
    assert rejected.json()["decision"]["reason"]

    provenance = client.get(f"/api/v1/suggestions/{target['id']}/provenance", headers=headers)
    assert provenance.status_code == 200


def test_hitl_v2_consent_required_before_extraction(client: TestClient) -> None:
    """V2 — AI consent required before extraction."""
    tokens = register_org(client, slug=f"hitl-v2-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])
    patient_id, encounter_id, _ = _clinical_setup(client, headers)

    session = client.post(f"/api/v1/encounters/{encounter_id}/sessions", headers=headers, json={})
    session_id = session.json()["id"]

    blocked = client.post(f"/api/v1/sessions/{session_id}/extract", headers=headers)
    assert blocked.status_code == 403
