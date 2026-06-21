"""Security hardening tests (Phase 6)."""

from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def test_security_headers_on_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_security_headers_on_api(client: TestClient) -> None:
    tokens = register_org(client)
    response = client.get("/api/v1/auth/me", headers=auth_headers(tokens["access_token"]))
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_unauthenticated_api_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/v1/patients")
    assert response.status_code == 401
    body = response.json()
    assert body["code"]
    assert body["status"] == 401


def test_invalid_login_does_not_leak_user_existence(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing-user@example.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
