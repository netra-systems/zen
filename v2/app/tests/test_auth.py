import pytest
import os
import datetime
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from app.db.models_postgres import User
from app.dependencies import get_current_user
from app.main import app

# Mock all settings using environment variables
@pytest.fixture(scope="module", autouse=True)
def mock_settings():
    with patch.dict('os.environ', {
        'environment': 'testing',
        'SECRET_KEY': 'a_very_secret_key_that_is_32_bytes',
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpassword',
        'POSTGRES_DB': 'testdb',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'CLICKHOUSE_HOST': 'localhost',
        'CLICKHOUSE_PORT': '9000',
        'CLICKHOUSE_USER': 'default',
        'CLICKHOUSE_PASSWORD': '',
        'CLICKHOUSE_DATABASE': 'testdb',
        'OPENAI_API_KEY': 'test_key',
        'GOOGLE_API_KEY': 'test_key',
        'ANTHROPIC_API_KEY': 'test_key',
        'GOOGLE_CLIENT_ID': 'test_id',
        'GOOGLE_CLIENT_SECRET': 'test_secret',
        'GOOGLE_REDIRECT_URI': 'http://localhost/auth/google/callback',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
    }, clear=True):
        yield

# Module-scoped mock for the database session
@pytest.fixture(scope="module")
def mock_db_session_module():
    return AsyncMock(spec=AsyncSession)

# This fixture creates the test client and handles dependency overrides
@pytest.fixture(scope="module")
def client(mock_db_session_module):
    mock_key_manager = MagicMock()
    mock_key_manager.fernet_key = Fernet.generate_key()
    mock_key_manager.jwt_secret_key = os.environ['SECRET_KEY']

    with patch('app.main.KeyManager.load_from_settings', return_value=mock_key_manager), \
         patch('app.main.LLMManager', autospec=True), \
         patch('app.logging_config.central_logger.clickhouse_db', autospec=True), \
         patch('app.main.NetraOptimizerAgentSupervisor', autospec=True), \
         patch('app.main.StreamingAgentSupervisor', autospec=True), \
         patch('app.main.AgentService', autospec=True):

        from app.db.postgres import get_async_db

        async def override_get_db():
            yield mock_db_session_module

        app.dependency_overrides[get_async_db] = override_get_db
        
        with TestClient(app) as c:
            yield c
    
        app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def reset_db_mock(mock_db_session_module):
    mock_db_session_module.reset_mock()
    mock_db_session_module.execute.reset_mock()
    mock_db_session_module.execute.side_effect = None
    mock_db_session_module.commit.reset_mock()
    mock_db_session_module.refresh.reset_mock()

# --- Test Cases for /token endpoint ---

def test_login_for_access_token_success(client, mock_db_session_module):
    hashed_password = b'$2b$12$EixZAe3.L2sE5.DV4.fL6u6K0DP.YVjYmJzT8S.C/c8Q9g5u3v5yO' # "password"
    mock_user = User(email="test@example.com", hashed_password=hashed_password, is_active=True)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session_module.execute.return_value = mock_result

    with patch('app.routes.auth.verify_password', return_value=True) as mock_verify_password:
        response = client.post("/auth/token", data={"username": "test@example.com", "password": "password"})
        
        assert response.status_code == 200
        json_response = response.json()
        assert "access_token" in json_response
        assert json_response["token_type"] == "bearer"
        mock_verify_password.assert_called_once_with("password", mock_user.hashed_password)

def test_login_for_access_token_incorrect_password(client, mock_db_session_module):
    mock_user = User(email="test@example.com", hashed_password="wrong_hash", is_active=True)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session_module.execute.return_value = mock_result

    with patch('app.routes.auth.verify_password', return_value=False):
        response = client.post("/auth/token", data={"username": "test@example.com", "password": "wrong_password"})
        
        assert response.status_code == 401
        assert response.json() == {"detail": "Incorrect email or password"}

def test_login_for_access_token_user_not_found(client, mock_db_session_module):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session_module.execute.return_value = mock_result

    response = client.post("/auth/token", data={"username": "nonexistent@example.com", "password": "password"})
    
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}

def test_login_for_access_token_inactive_user(client, mock_db_session_module):
    mock_user = User(email="inactive@example.com", hashed_password="some_hash", is_active=False)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session_module.execute.return_value = mock_result

    with patch('app.routes.auth.verify_password', return_value=True):
        response = client.post("/auth/token", data={"username": "inactive@example.com", "password": "password"})
        
        assert response.status_code == 400
        assert response.json() == {"detail": "Inactive user"}

# --- Test Cases for /users endpoint ---

def test_create_user_success(client, mock_db_session_module):
    mock_result_existing = MagicMock()
    mock_result_existing.scalar_one_or_none.return_value = None
    mock_db_session_module.execute.return_value = mock_result_existing

    async def refresh_side_effect(user_obj):
        user_obj.id = str(uuid.uuid4())
        user_obj.created_at = datetime.datetime.now(datetime.timezone.utc)

    mock_db_session_module.refresh.side_effect = refresh_side_effect

    with patch('app.routes.auth.get_password_hash', return_value="hashed_password") as mock_get_hash:
        user_data = {"email": "newuser@example.com", "password": "newpassword", "full_name": "New User"}
        response = client.post("/auth/users", json=user_data)

        assert response.status_code == 201
        json_response = response.json()
        assert json_response["email"] == "newuser@example.com"
        assert json_response["full_name"] == "New User"
        assert "id" in json_response
        mock_get_hash.assert_called_once_with("newpassword")
        mock_db_session_module.add.assert_called_once()
        mock_db_session_module.commit.assert_awaited_once()
        mock_db_session_module.refresh.assert_awaited_once()

def test_create_user_email_already_registered(client, mock_db_session_module):
    mock_existing_user = User(email="existing@example.com", hashed_password="some_hash", is_active=True)
    mock_result_existing = MagicMock()
    mock_result_existing.scalar_one_or_none.return_value = mock_existing_user
    mock_db_session_module.execute.return_value = mock_result_existing

    user_data = {"email": "existing@example.com", "password": "password", "full_name": "Existing User"}
    response = client.post("/auth/users", json=user_data)

    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

# --- Test Cases for /users/me endpoint ---

@pytest.fixture
def authenticated_client(client):
    mock_user = User(
        id=str(uuid.uuid4()),
        email="test@example.com", 
        full_name="Test User",
        hashed_password="test_password", 
        is_active=True, 
        created_at=datetime.datetime.now(datetime.timezone.utc),
        picture="http://example.com/pic.jpg"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client, mock_user
    del app.dependency_overrides[get_current_user]

def test_read_users_me(authenticated_client):
    client, _ = authenticated_client
    response = client.get("/auth/users/me")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["email"] == "test@example.com"
    assert json_response["full_name"] == "Test User"
    assert json_response["picture"] == "http://example.com/pic.jpg"

def test_update_user_me(authenticated_client, mock_db_session_module):
    client, mock_user = authenticated_client
    update_data = {"email": mock_user.email, "full_name": "Updated Test User"}
    
    async def refresh_side_effect(user_obj):
        # When refresh is called, update the mock_user object to simulate the DB update
        mock_user.full_name = update_data["full_name"]

    mock_db_session_module.refresh.side_effect = refresh_side_effect

    response = client.put("/auth/users/me", json=update_data)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["full_name"] == "Updated Test User"
    mock_db_session_module.add.assert_called_once()
    mock_db_session_module.commit.assert_awaited_once()
    mock_db_session_module.refresh.assert_awaited_once()

def test_delete_user_me(authenticated_client, mock_db_session_module):
    client, _ = authenticated_client
    response = client.delete("/auth/users/me")
    assert response.status_code == 204
    mock_db_session_module.delete.assert_called_once()
    mock_db_session_module.commit.assert_awaited_once()