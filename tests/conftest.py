import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Generator
import asyncio

# Set testing environment variables
os.environ["TESTING"] = "1"
os.environ["REDIS_HOST"] = "localhost"
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Set authentication secrets required for tests
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-do-not-use-in-production"
os.environ["FERNET_KEY"] = "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao="  # Test key only
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-chars-long"

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Only import if available to avoid failures
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Mock User class if app imports fail
try:
    from app.schemas import User
except ImportError:
    class User:
        def __init__(self, id, email, is_active=True, is_superuser=False):
            self.id = id
            self.email = email
            self.is_active = is_active
            self.is_superuser = is_superuser

pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Don't close loop to avoid hanging

@pytest.fixture
def mock_redis_manager():
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    return mock

@pytest.fixture
def mock_clickhouse_client():
    mock = MagicMock()
    mock.ping = MagicMock(return_value=True)
    mock.execute = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock()
    mock.get_llm = MagicMock(return_value=MagicMock())
    return mock

@pytest.fixture
def mock_websocket_manager():
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.send_message = AsyncMock(return_value=None)
    mock.broadcast = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_background_task_manager():
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_key_manager():
    mock = MagicMock()
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock

@pytest.fixture
def mock_security_service():
    return MagicMock()

@pytest.fixture
def mock_tool_dispatcher():
    return MagicMock()

@pytest.fixture
def mock_agent_supervisor():
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_agent_service():
    return MagicMock()

@pytest.fixture
def app(
    mock_redis_manager,
    mock_clickhouse_client,
    mock_llm_manager,
    mock_websocket_manager,
    mock_background_task_manager,
    mock_key_manager,
    mock_security_service,
    mock_tool_dispatcher,
    mock_agent_supervisor,
    mock_agent_service,
):
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
        
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.redis_manager = mock_redis_manager
        app.state.clickhouse_client = mock_clickhouse_client
        app.state.llm_manager = mock_llm_manager
        app.state.background_task_manager = mock_background_task_manager
        app.state.key_manager = mock_key_manager
        app.state.security_service = mock_security_service
        app.state.tool_dispatcher = mock_tool_dispatcher
        app.state.agent_supervisor = mock_agent_supervisor
        app.state.agent_service = mock_agent_service
        yield
    
    app = FastAPI(lifespan=lifespan)
    
    # Only include routes if they can be imported
    try:
        from app.routes.websockets import router as websockets_router
        app.include_router(websockets_router)
    except ImportError:
        pass
        
    try:
        from app.routes.auth import router as auth_router
        app.include_router(auth_router, prefix="/api/auth")
    except ImportError:
        pass
        
    return app

@pytest.fixture
def client(app):
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
    return TestClient(app)

@pytest.fixture
def test_user():
    return User(
        id="test-user-id",
        email="test@example.com",
        is_active=True,
        is_superuser=False
    )

@pytest.fixture
def auth_headers(test_user):
    try:
        from app.auth.auth import create_access_token
        token = create_access_token(data={"sub": test_user.email})
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers if auth module not available
        return {"Authorization": "Bearer mock-token"}

# Simple fixture for basic testing
@pytest.fixture
def sample_data():
    return {"test": "data"}