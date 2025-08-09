
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.ws_manager import manager
from app.schemas import User, TokenPayload
import uuid
from app.services.security_service import SecurityService
from app.services.key_manager import KeyManager
from app.config import settings

@pytest.fixture(scope="module")
def key_manager():
    return KeyManager(jwt_secret_key=settings.jwt_secret_key, fernet_key=settings.fernet_key)

@pytest.fixture(scope="module")
def security_service(key_manager: KeyManager):
    return SecurityService(key_manager)

@pytest.fixture
def client():
    # Clear any previous dependency overrides
    app.dependency_overrides = {}
    return TestClient(app)

@pytest.fixture
def active_user() -> User:
    return User(id=str(uuid.uuid4()), email="test@example.com", is_superuser=False, is_active=True)

@pytest.mark.asyncio
async def test_websocket_connection(client: TestClient, active_user: User, security_service: SecurityService):
    token_payload = TokenPayload(sub=str(active_user.id))
    token = security_service.create_access_token(data=token_payload)
    
    # Mock the database call to avoid hitting the actual database
    async def mock_get_user_by_id(db_session, user_id):
        if user_id == str(active_user.id):
            return active_user
        return None

    security_service.get_user_by_id = mock_get_user_by_id

    app.dependency_overrides[SecurityService] = lambda: security_service

    try:
        with client.websocket_connect(f"/ws/{token}") as websocket:
            user_id = str(active_user.id)
            # Check if the connection is active for the user
            assert user_id in manager.active_connections
            assert websocket in manager.active_connections[user_id]
            
            # Test sending and receiving a message
            test_message = "hello"
            websocket.send_text(test_message)
            response = websocket.receive_json()
            assert response == {"message": test_message}

    finally:
        # Clean up manager state and dependency overrides
        manager.disconnect(str(active_user.id), websocket)
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_websocket_disconnect(client: TestClient, active_user: User, security_service: SecurityService):
    token_payload = TokenPayload(sub=str(active_user.id))
    token = security_service.create_access_token(data=token_payload)

    # Mock the database call
    async def mock_get_user_by_id(db_session, user_id):
        return active_user
    security_service.get_user_by_id = mock_get_user_by_id
    app.dependency_overrides[SecurityService] = lambda: security_service

    user_id = str(active_user.id)
    
    with client.websocket_connect(f"/ws/{token}") as websocket:
        assert user_id in manager.active_connections
    
    # After the 'with' block, the disconnect should have been called
    assert user_id not in manager.active_connections
    
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_websocket_unauthorized_bad_token(client: TestClient):
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/this_is_a_bad_token") as websocket:
            pass
    assert excinfo.value.code == 4001 # Custom code for auth failure

@pytest.mark.asyncio
async def test_websocket_unauthorized_inactive_user(client: TestClient, active_user: User, security_service: SecurityService):
    active_user.is_active = False # Deactivate user
    token_payload = TokenPayload(sub=str(active_user.id))
    token = security_service.create_access_token(data=token_payload)

    async def mock_get_user_by_id(db_session, user_id):
        return active_user
    security_service.get_user_by_id = mock_get_user_by_id
    app.dependency_overrides[SecurityService] = lambda: security_service

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/ws/{token}") as websocket:
            pass
    assert excinfo.value.code == 4001
    
    app.dependency_overrides = {}
