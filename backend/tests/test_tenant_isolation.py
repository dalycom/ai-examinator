from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.base_repository import TenantScopedRepository
from app.core.database import tenant_session
from app.core.models import Clinic, User
from tests.test_auth import auth_headers, register_org


def test_org_a_cannot_read_org_b_clinic_via_api(client: TestClient, db: Session) -> None:
    org_a = register_org(client, slug=f"org-a-{uuid4().hex[:8]}")
    org_b = register_org(client, slug=f"org-b-{uuid4().hex[:8]}")

    create_a = client.post(
        "/api/v1/clinics",
        headers=auth_headers(org_a["access_token"]),
        json={"name": "Clinic A", "timezone": "UTC"},
    )
    assert create_a.status_code == 201
    clinic_a_id = create_a.json()["id"]

    cross_read = client.get(
        f"/api/v1/clinics/{clinic_a_id}",
        headers=auth_headers(org_b["access_token"]),
    )
    assert cross_read.status_code == 404

    me_b = client.get("/api/v1/auth/me", headers=auth_headers(org_b["access_token"]))
    org_b_id = me_b.json()["organization_id"]

    with tenant_session(db, org_b_id):
        repo = TenantScopedRepository[Clinic](db, org_b_id)
        leaked = repo.scoped_query(Clinic).filter(Clinic.name == "Clinic A").all()
        assert leaked == []


def test_repository_scoping_blocks_cross_org_user_lookup(client: TestClient, db: Session) -> None:
    org_a = register_org(client, slug=f"scope-a-{uuid4().hex[:8]}")
    org_b = register_org(client, slug=f"scope-b-{uuid4().hex[:8]}")

    me_a = client.get("/api/v1/auth/me", headers=auth_headers(org_a["access_token"]))
    me_b = client.get("/api/v1/auth/me", headers=auth_headers(org_b["access_token"]))

    with tenant_session(db, me_b.json()["organization_id"]):
        repo = TenantScopedRepository[User](db, me_b.json()["organization_id"])
        users = repo.scoped_query(User).filter(User.email == me_a.json()["email"]).all()
        assert users == []
