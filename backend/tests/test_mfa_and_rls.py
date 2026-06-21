import os
from uuid import uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.models import Clinic
from tests.test_auth import auth_headers, register_org


@pytest.fixture()
def app_db_engine():
    app_url = os.getenv(
        "APP_DATABASE_URL",
        "postgresql+psycopg://ai_examinator_app:change_me_in_local_env@localhost:5433/ai_examinator_test",
    )
    engine = create_engine(app_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_rls_hides_other_org_rows_from_app_role(app_db_engine, client: TestClient) -> None:
    org_a = register_org(client, slug="rls-org-a")
    org_b = register_org(client, slug="rls-org-b")

    create_a = client.post(
        "/api/v1/clinics",
        headers=auth_headers(org_a["access_token"]),
        json={"name": "RLS Clinic A", "timezone": "UTC"},
    )
    assert create_a.status_code == 201

    me_b = client.get("/api/v1/auth/me", headers=auth_headers(org_b["access_token"]))
    org_b_id = me_b.json()["organization_id"]

    session = sessionmaker(bind=app_db_engine)()
    try:
        session.execute(
            text("SELECT set_config('app.current_organization_id', :org_id, true)"),
            {"org_id": str(org_b_id)},
        )
        leaked_clinics = session.query(Clinic).filter(Clinic.name == "RLS Clinic A").all()
        assert leaked_clinics == []
    finally:
        session.close()


def test_mfa_enroll_confirm_and_login(client: TestClient) -> None:
    tokens = register_org(client, slug=f"mfa-{uuid4().hex[:8]}")
    headers = auth_headers(tokens["access_token"])

    enroll = client.post("/api/v1/auth/mfa/enroll", headers=headers)
    assert enroll.status_code == 200
    secret = enroll.json()["secret"]
    code = pyotp.TOTP(secret).now()

    confirm = client.post("/api/v1/auth/mfa/confirm", headers=headers, json={"code": code})
    assert confirm.status_code == 204

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": me.json()["email"], "password": "TestPassword123!"},
    )
    assert login.status_code == 200
    assert login.json()["mfa_required"] is True
    assert login.json()["mfa_token"]
