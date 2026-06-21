from fastapi.testclient import TestClient

from tests.test_auth import auth_headers, register_org


def test_audit_log_is_hash_chained(client: TestClient) -> None:
    tokens = register_org(client)
    client.post(
        "/api/v1/clinics",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Audit Clinic", "timezone": "UTC"},
    )

    logs = client.get("/api/v1/audit-logs", headers=auth_headers(tokens["access_token"]))
    assert logs.status_code == 200
    entries = sorted(logs.json(), key=lambda entry: entry["created_at"])
    assert len(entries) >= 2
    assert entries[0]["prev_hash"] is None
    for index in range(1, len(entries)):
        assert entries[index]["prev_hash"] == entries[index - 1]["record_hash"]
