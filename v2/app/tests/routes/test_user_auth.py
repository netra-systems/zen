
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.config import settings
from app.db.base import Base
from app.db.testing import engine
from app.dependencies import get_db_session
from app.db.testing import override_get_db

app.dependency_overrides[get_db_session] = override_get_db

@pytest_asyncio.fixture(scope="function")
async def client(test_db) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture(scope="function")
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_auth_config_dev_mode(client: AsyncClient):
    settings.environment = "development"
    response = await client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["development_mode"] is True
    assert data["endpoints"]["dev_login"] is not None

@pytest.mark.asyncio
async def test_get_auth_config_prod_mode(client: AsyncClient):
    settings.environment = "production"
    response = await client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["development_mode"] is False

@pytest.mark.asyncio
async def test_dev_login_get_not_allowed(client: AsyncClient):
    settings.environment = "development"
    response = await client.get("/api/auth/dev_login", follow_redirects=False)
    assert response.status_code == 405  # Method Not Allowed

@pytest.mark.asyncio
async def test_dev_login_success(client: AsyncClient):
    settings.environment = "development"
    response = await client.post("/api/auth/dev_login", json={"email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Dev login successful"
    assert data["user"] == "test@example.com"

@pytest.mark.asyncio
async def test_dev_login_prod_mode(client: AsyncClient):
    settings.environment = "production"
    response = await client.post("/api/auth/dev_login", json={"email": "test@example.com"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_google_login_redirect(client: AsyncClient):
    response = await client.get("/api/auth/login/google", follow_redirects=False)
    assert response.status_code == 302  # Found
    assert "accounts.google.com" in response.headers["location"]

@pytest.mark.asyncio
async def test_logout_redirect(client: AsyncClient):
    response = await client.get("/api/auth/logout", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect
    assert response.headers["location"] == "/login"
