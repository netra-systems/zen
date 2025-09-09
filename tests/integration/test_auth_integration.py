import os
import asyncio
import pytest
from fastapi.testclient import TestClient
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.database_skip_conditions import DatabaseAvailabilityChecker

# Get environment instance first
env = get_env()

# Set environment to development for dev login endpoint to work
env.set("NETRA_ENVIRONMENT", "development", "test")

from auth_service.main import app
from auth_service.auth_core.database.connection import auth_db

client = TestClient(app)
@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup database tables before running tests.
    
    FIXED: Changed from module to function scope to resolve fixture conflicts.
    """
    # Skip if database unavailable
    availability_checker = DatabaseAvailabilityChecker()
    is_available, reason = availability_checker.check_postgresql_available()
    if not is_available:
        pytest.skip(f"PostgreSQL unavailable: {reason}")
    
    async def create_tables():
        # Initialize the database connection first
        await auth_db.initialize()
        # Now create tables
        await auth_db.create_tables()
    
    # Create tables before tests
    asyncio.run(create_tables())
    yield
    # Cleanup is handled by the database connection itself


@pytest.fixture(scope="module")
def test_user():
    # Create a test user in the database
    # This would require a database connection and user creation logic
    # For now, we'll just return a dummy user
    return {"email": "test@example.com", "password": "testpassword"}


def test_dev_login():
    # Ensure environment is set to development for this test
    original_env = env.get("NETRA_ENVIRONMENT")
    env.set("NETRA_ENVIRONMENT", "development", "test")
    
    try:
        response = client.post("/auth/dev/login")
        assert response.status_code == 200
        assert "access_token" in response.json()
    finally:
        # Restore original environment
        if original_env:
            env.set("NETRA_ENVIRONMENT", original_env, "test")
        elif "NETRA_ENVIRONMENT" in os.environ:
            env.delete("NETRA_ENVIRONMENT", "test")


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
