from uuid import uuid4

from fastapi.testclient import TestClient


def register_org(client: TestClient, slug: str | None = None) -> dict:
    slug = slug or f"org-{uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Test Org {slug}",
            "organization_slug": slug,
            "admin_email": f"admin+{slug}@example.com",
            "admin_full_name": "Test Admin",
            "admin_password": "TestPassword123!",
            "default_locale": "en",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_and_me(client: TestClient) -> None:
    tokens = register_org(client)
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me = client.get("/api/v1/auth/me", headers=auth_headers(tokens["access_token"]))
    assert me.status_code == 200
    body = me.json()
    assert body["full_name"] == "Test Admin"
    assert "org:manage" in body["permissions"]


def test_login_with_email_password(client: TestClient) -> None:
    slug = f"login-{uuid4().hex[:8]}"
    email = f"doctor+{slug}@example.com"
    password = "TestPassword123!"
    register_org(
        client,
        slug=slug,
    )
    # register_org creates admin with admin+{slug}@example.com — login with register credentials
    login = client.post(
        "/api/v1/auth/login",
        json={"email": f"admin+{slug}@example.com", "password": password},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


def test_refresh_token_rotation(client: TestClient) -> None:
    tokens = register_org(client)
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"]


def test_create_clinic_requires_permission(client: TestClient) -> None:
    tokens = register_org(client)
    response = client.post(
        "/api/v1/clinics",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Main Clinic", "timezone": "UTC"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Main Clinic"
