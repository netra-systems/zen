import pytest
from fastapi.testclient import TestClient

from auth_service.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def test_user():
    # Create a test user in the database
    # This would require a database connection and user creation logic
    # For now, we'll just return a dummy user
    return {"email": "test@example.com", "password": "testpassword"}


def test_dev_login():
    response = client.post("/auth/dev/login")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_logout(test_user):
    # Login
    response = client.post("/auth/login", json=test_user)
    assert response.status_code == 200
    assert "access_token" in response.json()
    access_token = response.json()["access_token"]

    # Validate the token
    response = client.post("/auth/validate", json={"token": access_token})
    assert response.status_code == 200
    assert response.json()["valid"] == True

    # Logout
    response = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True

    # Validate the token again (should be invalid)
    response = client.post("/auth/validate", json={"token": access_token})
    assert response.status_code == 401


def test_refresh_token(test_user):
    # Login to get a refresh token
    response = client.post("/auth/login", json=test_user)
    assert response.status_code == 200
    refresh_token = response.json()["refresh_token"]

    # Refresh the token
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
