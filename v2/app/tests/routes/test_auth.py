import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security_service import get_password_hash
from app.db.models_postgres import User

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, db_session: AsyncSession):
    # Arrange
    password = "testpassword"
    hashed_password = get_password_hash(password)
    user = User(email="test@example.com", hashed_password=hashed_password)
    db_session.add(user)
    await db_session.commit()

    # Act
    response = await client.post("/auth/token", data={"username": "test@example.com", "password": password})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_for_access_token_invalid_credentials(client: AsyncClient):
    # Act
    response = await client.post("/auth/token", data={"username": "wrong@example.com", "password": "wrongpassword"})

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, db_session: AsyncSession):
    # Arrange
    password = "testpassword"
    hashed_password = get_password_hash(password)
    user = User(email="test@example.com", hashed_password=hashed_password)
    db_session.add(user)
    await db_session.commit()
    response = await client.post("/auth/token", data={"username": "test@example.com", "password": password})
    token = response.json()["access_token"]

    # Act
    response = await client.get("/auth/users/me", headers={"Authorization": f"Bearer {token}"})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_read_users_me_invalid_token(client: AsyncClient):
    # Act
    response = await client.get("/auth/users/me", headers={"Authorization": "Bearer invalidtoken"})

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED