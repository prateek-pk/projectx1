from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_protected_endpoint_rejects_missing_token():
    response = client.post(
        "/users/me",
        json={"name": "Test User"},
    )

    assert response.status_code == 401

def test_protected_endpoint_rejects_invalid_token():
    response = client.post(
        "/users/me",
        json={"name": "Test User"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401